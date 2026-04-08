import { useRef } from 'react';
import { GetStaticPaths, GetStaticProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import styled from 'styled-components';
import WikiLayout from '@/components/wiki/wiki-layout';
import WikiArticleView from '@/components/wiki/wiki-article';
import WikiMargin from '@/components/wiki/wiki-toc';
import { getArticleSlugs, getArticleBySlug, getAllArticles } from '@/utils/wiki-loader';
import type { WikiArticle, WikiIndexEntry } from '@/types/wiki';

const Crumbs = styled.div`
  font-size: 12px;
  color: #b0b0ac;
  margin-bottom: 20px;

  a {
    color: #b0b0ac;
    text-decoration: none;
    &::before, &::after { display: none !important; }
  }

  a:hover {
    color: #0080ff;
  }
`;

const ArticleGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 180px;
  gap: 40px;

  @media (max-width: 1100px) {
    grid-template-columns: 1fr;
  }
`;

const ArticleContent = styled.div`
  min-width: 0;
`;

interface WikiArticlePageProps {
  article: WikiArticle;
  articles: WikiIndexEntry[];
}

export default function WikiArticlePage({ article, articles }: WikiArticlePageProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  return (
    <>
      <Head>
        <title>{article.title} - Wiki</title>
        <meta name="robots" content="noindex" />
      </Head>
      <WikiLayout articles={articles}>
        <Crumbs>
          <Link href="/wiki">Wiki</Link>
          {article.directory && (
            <>
              {' / '}
              <Link href={`/wiki#${article.directory}`}>{article.directory}</Link>
            </>
          )}
          {' / '}
          {article.title}
        </Crumbs>
        <ArticleGrid>
          <ArticleContent ref={contentRef}>
            <WikiArticleView article={article} />
          </ArticleContent>
          <WikiMargin article={article} contentRef={contentRef} />
        </ArticleGrid>
      </WikiLayout>
    </>
  );
}

export const getStaticPaths: GetStaticPaths = async () => {
  const slugs = getArticleSlugs();
  return {
    paths: slugs.map((slug) => ({
      params: { slug: slug.split('/') },
    })),
    fallback: 'blocking',
  };
};

export const getStaticProps: GetStaticProps = async ({ params }) => {
  const slugParts = params?.slug as string[];
  const slug = slugParts.join('/');
  const article = await getArticleBySlug(slug);

  if (!article) {
    return { notFound: true };
  }

  const articles = getAllArticles();

  return {
    props: { article, articles },
    revalidate: 3600,
  };
};
