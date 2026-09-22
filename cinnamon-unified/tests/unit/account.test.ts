import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { initDatabase, closeDatabase } from '@db/connection';
import { getDatabase } from '@db/connection';
import { AccountService } from '../../apps/bot/src/account/account.service';
import { eq } from 'drizzle-orm';
import { accounts, profiles, wallets, recoveryCodes, identities } from '@db/schema';

describe('AccountService', () => {
  let accountService: AccountService;

  beforeAll(async () => {
    await initDatabase();
    accountService = new AccountService();
  });

  afterAll(() => {
    closeDatabase();
  });

  it('should register a new account with UUID', async () => {
    const result = await accountService.register({
      password: 'testPassword123',
      displayName: 'TestUser',
    });

    expect(result.accountId).toBeDefined();
    expect(result.recoveryCodes).toHaveLength(10);
    expect(typeof result.accountId).toBe('string');

    // Verify account exists in database
    const db = getDatabase();
    const account = await db.query.accounts.findFirst({
      where: eq(accounts.id, result.accountId),
    });

    expect(account).toBeDefined();
    expect(account?.status).toBe('active');

    // Verify profile was created
    const profile = await db.query.profiles.findFirst({
      where: eq(profiles.accountId, result.accountId),
    });

    expect(profile).toBeDefined();
    expect(profile?.displayName).toBe('TestUser');
    expect(profile?.rank).toBe('user');
    expect(profile?.level).toBe(1);

    // Verify wallet was created
    const wallet = await db.query.wallets.findFirst({
      where: eq(wallets.accountId, result.accountId),
    });

    expect(wallet).toBeDefined();
    expect(wallet?.balance).toBe(0);
    expect(wallet?.bankBalance).toBe(0);

    // Verify recovery codes were created
    const codes = await db.query.recoveryCodes.findMany({
      where: eq(recoveryCodes.accountId, result.accountId),
    });

    expect(codes).toHaveLength(10);
    expect(codes.every(c => !c.used)).toBe(true);
  });

  it('should login with correct credentials', async () => {
    const registerResult = await accountService.register({
      password: 'loginTest123',
      displayName: 'LoginUser',
    });

    const loginResult = await accountService.login({
      accountId: registerResult.accountId,
      password: 'loginTest123',
    });

    expect(loginResult.valid).toBe(true);
    expect(loginResult.accountId).toBe(registerResult.accountId);
  });

  it('should fail login with wrong password', async () => {
    const registerResult = await accountService.register({
      password: 'correctPassword',
      displayName: 'WrongPassUser',
    });

    const loginResult = await accountService.login({
      accountId: registerResult.accountId,
      password: 'wrongPassword',
    });

    expect(loginResult.valid).toBe(false);
  });

  it('should recover account with valid recovery code', async () => {
    const registerResult = await accountService.register({
      password: 'recoverTest123',
      displayName: 'RecoverUser',
    });

    const recoveryCode = registerResult.recoveryCodes[0];

    const recoverResult = await accountService.recover({
      accountId: registerResult.accountId,
      recoveryCode: recoveryCode,
    });

    expect(recoverResult.success).toBe(true);

    const db = getDatabase();
    const codeRecord = await db.query.recoveryCodes.findFirst({
      where: eq(recoveryCodes.accountId, registerResult.accountId),
    });

    expect(codeRecord?.used).toBe(true);
  });

  it('should fail recovery with invalid code', async () => {
    const registerResult = await accountService.register({
      password: 'invalidRecover123',
      displayName: 'InvalidRecoverUser',
    });

    const recoverResult = await accountService.recover({
      accountId: registerResult.accountId,
      recoveryCode: 'INVALID-CODE',
    });

    expect(recoverResult.success).toBe(false);
    expect(recoverResult.message).toContain('Invalid');
  });

  it('should link identity to account', async () => {
    const registerResult = await accountService.register({
      password: 'identityTest123',
      displayName: 'IdentityUser',
    });

    await accountService.linkIdentity(
      registerResult.accountId,
      'whatsapp:pn',
      '628123456789'
    );

    const account = await accountService.getAccount(registerResult.accountId);
    expect(account?.identities).toHaveLength(1);
    expect(account?.identities[0].identifier).toBe('628123456789');
  });

  it('should resolve identity to account_id', async () => {
    const registerResult = await accountService.register({
      password: 'resolveTest123',
      displayName: 'ResolveUser',
    });

    await accountService.linkIdentity(
      registerResult.accountId,
      'whatsapp:lid',
      '1234567890'
    );

    const resolvedAccountId = await accountService.resolveIdentity(
      'whatsapp:lid',
      '1234567890'
    );

    expect(resolvedAccountId).toBe(registerResult.accountId);
  });

  it('should throw IDENTITY_CONFLICT when linking duplicate identity', async () => {
    const user1 = await accountService.register({
      password: 'conflict1',
      displayName: 'User1',
    });

    const user2 = await accountService.register({
      password: 'conflict2',
      displayName: 'User2',
    });

    await accountService.linkIdentity(user1.accountId, 'whatsapp:pn', '999888777');

    await expect(
      accountService.linkIdentity(user2.accountId, 'whatsapp:pn', '999888777')
    ).rejects.toThrow('IDENTITY_CONFLICT');
  });
});
