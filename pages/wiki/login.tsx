import { useState, FormEvent } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import styled from 'styled-components';

const LoginWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 24px;
`;

const LoginTitle = styled.h1`
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
`;

const LoginForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 280px;
`;

const Input = styled.input`
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  font-family: inherit;
  border: 1px solid #ddd;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.15s ease;

  &:focus {
    border-color: #0080ff;
  }
`;

const ErrorText = styled.p`
  color: #ef4444;
  font-size: 13px;
  text-align: center;
`;

export default function WikiLogin() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const redirect = (router.query.redirect as string) || '/wiki';

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/wiki/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        router.push(redirect);
      } else {
        setError('Wrong password');
      }
    } catch {
      setError('Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Wiki</title>
        <meta name="robots" content="noindex" />
      </Head>
      <LoginWrapper>
        <LoginTitle>Wiki</LoginTitle>
        <LoginForm onSubmit={handleSubmit}>
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
          <button className="btn" type="submit" disabled={loading}>
            {loading ? 'Checking...' : 'Enter'}
          </button>
          {error && <ErrorText>{error}</ErrorText>}
        </LoginForm>
      </LoginWrapper>
    </>
  );
}
