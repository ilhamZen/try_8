import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { initializeTables } from '../db/connection';
import * as pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

async function bootstrap() {
  try {
    // Initialize database
    logger.info('Initializing database...');
    initializeTables();

    // Create NestJS application
    const app = await NestFactory.create(AppModule, {
      logger: ['error', 'warn', 'log'],
    });

    // Enable shutdown hooks
    app.enableShutdownHooks();

    // Start application
    const port = process.env.PORT || 3000;
    await app.listen(port);
    
    logger.info(`Cinnamon R1F is running on port ${port}`);
    logger.info('Database initialized successfully');
    
    return app;
  } catch (error) {
    logger.error('Failed to start application:', error);
    throw error;
  }
}

// Bootstrap the application
bootstrap().catch((error) => {
  logger.error('Application bootstrap failed:', error);
  process.exit(1);
});

export { bootstrap };
