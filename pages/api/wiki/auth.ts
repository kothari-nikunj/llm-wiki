import type { NextApiRequest, NextApiResponse } from 'next';
import { SignJWT } from 'jose';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { password } = req.body;
  const expected = process.env.WIKI_PASSWORD;

  if (!expected) {
    return res.status(500).json({ error: 'WIKI_PASSWORD not configured' });
  }

  if (password !== expected) {
    return res.status(401).json({ error: 'Invalid password' });
  }

  const secret = new TextEncoder().encode(process.env.JWT_SECRET);
  const token = await new SignJWT({ wiki: true })
    .setProtectedHeader({ alg: 'HS256' })
    .setExpirationTime('30d')
    .sign(secret);

  res.setHeader(
    'Set-Cookie',
    `wiki_auth=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${30 * 24 * 60 * 60}${process.env.NODE_ENV === 'production' ? '; Secure' : ''}`
  );

  return res.status(200).json({ success: true });
}
