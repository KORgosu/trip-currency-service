import { FastifyInstance } from "fastify";
import { getTodayRanks, getTrending } from "../domain/leaderboard.js";

export default async function (fastify: FastifyInstance) {
  fastify.get("/ranks/today", async (req, reply) => {
    const q = req.query as any;
    const limit = Number(q.limit || 50);
    try {
      const ranks = await getTodayRanks(limit);
      return reply.send(ranks);
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: "read_failed" });
    }
  });

  fastify.get("/ranks/trending", async (req, reply) => {
    const q = req.query as any;
    const limit = Number(q.limit || 50);
    const decay = Number(q.decay || undefined) || undefined;
    try {
      const ranks = await getTrending(limit, decay);
      return reply.send(ranks);
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: "read_failed" });
    }
  });
}
