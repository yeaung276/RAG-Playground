from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.models.model import Model
from app.schemas.model import (
    ApiSchema,
    Capability,
    ModelCreate,
    ModelPage,
    ModelRead,
    ModelUpdate,
)
from app.services.errors import ConflictError, NotFoundError
from app.services.models.embedding import Embedder, OpenAIEmbedder, TEIEmbedder
from app.services.models.rerank import (
    CohereReranker,
    Reranker,
    TEILateInteractionReranker,
    TEIReranker,
)
from app.utils.crypto import decrypt_secret, encrypt_secret

logger = get_logger(__name__)


class ModelService:
    """CRUD for user-registered model endpoints. API keys are stored
    envelope-encrypted and never leave this service in plaintext except through
    `api_key_of`, used by the callers that make the outbound request."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: ModelCreate) -> ModelRead:
        model = Model(
            provider=payload.provider,
            schema=payload.api_schema,
            base_url=payload.base_url,
            name=payload.name,
            capability=payload.capability,
        )
        self.session.add(model)
        try:
            await self.session.flush()
            if payload.api_key:
                model.api_key_ct, model.api_key_dek = encrypt_secret(payload.api_key, model.id)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(f"{payload.name} is already registered for {payload.provider}")
        await self.session.refresh(model)
        return self._read(model)

    async def update(self, model_id: str, payload: ModelUpdate) -> ModelRead:
        model = await self._get(model_id)
        fields = payload.model_dump(exclude_unset=True)

        if "api_key" in fields:
            api_key = fields.pop("api_key")
            model.api_key_ct, model.api_key_dek = (
                encrypt_secret(api_key, model.id) if api_key else (None, None)
            )
        for field, value in fields.items():
            setattr(model, field, value)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(f"{model.name} is already registered for {model.provider}")
        await self.session.refresh(model)
        return self._read(model)

    async def list(
        self, page: int, page_size: int, capability: Capability | None = None
    ) -> ModelPage:
        where = [Model.capability == capability] if capability else []
        total = (
            await self.session.execute(select(func.count()).select_from(Model).where(*where))
        ).scalar_one()
        rows = (
            await self.session.execute(
                select(Model)
                .where(*where)
                .order_by(Model.provider, Model.created_at)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return ModelPage(
            items=[self._read(m) for m in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get(self, model_id: str) -> ModelRead:
        return self._read(await self._get(model_id))

    async def delete(self, model_id: str) -> None:
        await self.session.delete(await self._get(model_id))
        await self.session.commit()

    async def resolve_model(
        self, model_id: str | None, **kwargs
    ) -> BaseChatModel | Embedder | Reranker:
        """The registered row becomes a live client. Its capability decides which
        kind; `kwargs` go to that client's constructor (a decoder's temperature,
        for instance)."""
        if model_id is None:
            raise ConflictError("No model assigned")

        model = await self._get(model_id)
        api_key = await self.api_key_of(model_id)
        logger.info(
            "resolving %s name=%s schema=%s base_url=%s",
            model.capability, model.name, model.schema, model.base_url,
        )

        match model.capability, model.schema:
            case Capability.DECODER, _:
                return init_chat_model(
                    model.name,
                    model_provider=model.schema,
                    base_url=model.base_url,
                    api_key=api_key,
                    **kwargs,
                )
            case Capability.BI_ENCODER, ApiSchema.OPENAI:
                return OpenAIEmbedder(model.name, model.base_url, api_key, **kwargs)
            case Capability.BI_ENCODER, ApiSchema.TEI:
                return TEIEmbedder(model.name, model.base_url, api_key, **kwargs)
            case Capability.CROSS_ENCODER, ApiSchema.TEI:
                return TEIReranker(model.name, model.base_url, api_key, **kwargs)
            case Capability.CROSS_ENCODER, ApiSchema.COHERE:
                return CohereReranker(model.name, model.base_url, api_key, **kwargs)
            case Capability.LATE_INTERACTION, ApiSchema.TEI:
                return TEILateInteractionReranker(model.name, model.base_url, api_key, **kwargs)

        raise ConflictError(f"{model.schema} does not serve {model.capability} models")

    async def api_key_of(self, model_id: str) -> str | None:
        """Plaintext API key, for the caller that makes the outbound request."""
        model = await self._get(model_id)
        if model.api_key_ct is None or model.api_key_dek is None:
            return None
        return decrypt_secret(model.api_key_ct, model.api_key_dek, model.id)

    async def _get(self, model_id: str) -> Model:
        model = await self.session.get(Model, model_id)
        if model is None:
            raise NotFoundError(f"Model {model_id} not found")
        return model

    def _read(self, model: Model) -> ModelRead:
        return ModelRead(
            id=model.id,
            provider=model.provider,
            api_schema=model.schema,
            base_url=model.base_url,
            has_api_key=model.api_key_ct is not None,
            name=model.name,
            capability=model.capability,
            created_at=model.created_at,
        )
