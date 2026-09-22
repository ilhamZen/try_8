import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { db, initializeTables, closeDb } from '../../../db/connection';
import * as schema from '../../../db/schema';

@Injectable()
export class DbService implements OnModuleInit, OnModuleDestroy {
  async onModuleInit() {
    console.log('Initializing database connection...');
    initializeTables();
    console.log('Database connection established');
  }

  async onModuleDestroy() {
    console.log('Closing database connection...');
    closeDb();
  }

  getDb() {
    return db;
  }

  getSchema() {
    return schema;
  }
}
