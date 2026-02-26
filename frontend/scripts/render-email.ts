import { stdin, stdout, stderr, exit } from "node:process";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { getEmailTemplateElement } from "../src/components/emails/server/templates";

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString("utf8");
}

async function main() {
  const raw = (await readStdin()).trim();
  if (!raw) {
    throw new Error("Missing JSON payload on stdin");
  }

  const payload = JSON.parse(raw) as { template?: string; props?: Record<string, unknown> };
  const templateName = String(payload.template || "").trim();
  if (!templateName) {
    throw new Error("Missing template name");
  }

  const element = getEmailTemplateElement(templateName, payload.props ?? {});
  const html = "<!doctype html>" + renderToStaticMarkup(element);
  stdout.write(html);
}

main().catch((err) => {
  stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  exit(1);
});

