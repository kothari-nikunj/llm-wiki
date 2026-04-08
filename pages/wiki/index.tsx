import { GetStaticProps } from 'next';
import Head from 'next/head';
import ErrorBoundary from '@/components/error-boundary';
import WikiLayout from '@/components/wiki/wiki-layout';
import WikiIndex from '@/components/wiki/wiki-index';
import { getAllArticles } from '@/utils/wiki-loader';
import type { WikiIndexEntry } from '@/types/wiki';

interface WikiHomeProps {
  articles: WikiIndexEntry[];
}

export default function WikiHome({ articles }: WikiHomeProps) {
  return (
    <>
      <Head>
        <title>Wiki</title>
        <meta name="robots" content="noindex" />
      </Head>
      <WikiLayout isIndex articles={articles}>
        <ErrorBoundary>
          <WikiIndex articles={articles} />
        </ErrorBoundary>
      </WikiLayout>
    </>
  );
}

export const getStaticProps: GetStaticProps = async () => {
  const articles = getAllArticles();
  return {
    props: { articles },
    revalidate: 3600,
  };
};
