import { FastifyInstance } from "fastify";
import { recordClick } from "../domain/clicks.js";

export default async function (fastify: FastifyInstance) {
  fastify.post("/click", async (req, reply) => {
    const body = req.body as any;
    const country = (body?.country || "").toString().toUpperCase();
    if (!/^[A-Z]{2,3}$/.test(country)) {
      return reply.status(400).send({ error: "invalid country" });
    }

    try {
      await recordClick(country);
      return reply.send({ ok: true });
    } catch (err) {
      fastify.log.error(err);
      return reply.status(500).send({ error: "write_failed" });
    }
  });
}
