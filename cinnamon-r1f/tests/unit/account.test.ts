import { describe, it, expect, beforeEach } from 'vitest';
import { AccountService } from '../apps/bot/src/account/account.service';

describe('Account Service', () => {
  let accountService: AccountService;

  beforeEach(() => {
    // Note: This is a simplified test without actual DB connection
    // Integration tests should use a test database
    accountService = new AccountService();
  });

  describe('generateRecoveryCodes', () => {
    it('should generate correct number of recovery codes', () => {
      // Access private method via any cast for testing
      const codes = (accountService as any).generateRecoveryCodes(10);
      expect(codes).toHaveLength(10);
    });

    it('should generate codes in correct format XXXX-XXXX-XXXX-XXXX', () => {
      const codes = (accountService as any).generateRecoveryCodes(5);
      const codePattern = /^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/;
      
      codes.forEach((code: string) => {
        expect(code).toMatch(codePattern);
      });
    });

    it('should not contain I, O, 0, 1 characters', () => {
      const codes = (accountService as any).generateRecoveryCodes(10);
      
      codes.forEach((code: string) => {
        expect(code).not.toContain('I');
        expect(code).not.toContain('O');
        expect(code).not.toContain('0');
        expect(code).not.toContain('1');
      });
    });
  });
});
