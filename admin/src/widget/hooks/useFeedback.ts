import { useState } from 'react';
import { useWidgetConfig } from '../config';
import type { Feedback } from './useChat';

export function useFeedback(messageId: string) {
  const { backendUrl } = useWidgetConfig();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (value: Feedback | null) => {
    setIsSubmitting(true);
    try {
      const response = await fetch(
        `${backendUrl}/api/messages/${messageId}/feedback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ value }),
        },
      );
      return response.ok;
    } catch {
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  return { isSubmitting, submit };
}
