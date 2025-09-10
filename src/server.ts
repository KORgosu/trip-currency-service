import Fastify from "fastify";
import cors from '@fastify/cors';

const server = Fastify({ logger: true });

// enable CORS for browser-based frontend calls
server.register(cors, {
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'OPTIONS']
});

async function bootstrap() {
  const clicks = await import('./routes/clicks.js');
  const ranks = await import('./routes/ranks.js');
  server.register(clicks.default);
  server.register(ranks.default);

  const port = Number(process.env.PORT || 8000);
  try {
    await server.listen({ port, host: '0.0.0.0' });
    server.log.info(`listening ${port}`);
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
}

bootstrap();
