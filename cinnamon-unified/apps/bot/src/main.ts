import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { initDatabase, closeDatabase } from '../../../db/connection';
import { Logger } from 'pino';

async function bootstrap() {
  const logger = new Logger({ 
    level: process.env.LOG_LEVEL || 'info',
    transport: {
      target: 'pino-pretty',
      options: {
        colorize: true,
      },
    },
  });

  try {
    logger.info('🍂 Starting Cinnamon R1F...');
    
    // Initialize database
    logger.info('🗄️  Initializing database...');
    await initDatabase();
    logger.info('✅ Database ready');

    // Create NestJS application
    const app = await NestFactory.create(AppModule);
    
    // Enable shutdown hooks
    app.enableShutdownHooks();

    // Start application
    await app.init();
    
    logger.info('✅ Cinnamon R1F is running!');
    
    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      logger.warn('Received SIGINT, shutting down gracefully...');
      await app.close();
      closeDatabase();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      logger.warn('Received SIGTERM, shutting down gracefully...');
      await app.close();
      closeDatabase();
      process.exit(0);
    });

  } catch (error) {
    logger.error('Failed to start Cinnamon R1F:', error);
    closeDatabase();
    process.exit(1);
  }
}

bootstrap();
