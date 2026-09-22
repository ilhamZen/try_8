import { initDatabase, closeDatabase } from '../db/connection';

beforeAll(async () => {
  await initDatabase();
});

afterAll(async () => {
  closeDatabase();
});
