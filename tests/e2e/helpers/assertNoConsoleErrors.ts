import { Page, expect } from '@playwright/test';

export function assertNoConsoleErrors(page: Page) {
  const errors: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Ignore some common acceptable errors or false positives in development
      if (!text.includes('favicon.ico') && !text.includes('Failed to load resource')) {
        errors.push(text);
      }
    }
  });

  page.on('pageerror', (exception) => {
    errors.push(`Uncaught exception: ${exception.message}`);
  });

  page.on('requestfailed', (request) => {
    if (!request.url().includes('favicon.ico')) {
      errors.push(`Request failed: ${request.url()} - ${request.failure()?.errorText}`);
    }
  });
  
  page.on('response', (response) => {
    if (response.status() >= 500) {
      errors.push(`Server Error ${response.status()} for ${response.url()}`);
    }
  });

  return () => {
    if (errors.length > 0) {
      console.error('Console/Network Errors Detected:', errors);
      expect(errors.length, `Expected 0 console/network errors, but got ${errors.length}:\n${errors.join('\n')}`).toBe(0);
    }
  };
}
