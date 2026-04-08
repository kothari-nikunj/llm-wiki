import styled from 'styled-components';
import type { WikiArticle } from '@/types/wiki';

const ArticleHeader = styled.header`
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e8e8e6;
`;

const ArticleTitle = styled.h1`
  font-size: 24px;
  font-weight: 600;
  color: #37352f;
  line-height: 1.3;
  margin-bottom: 8px;
  letter-spacing: -0.3px;
`;

const MetaRow = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #9b9a97;
`;

const TypeBadge = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  background: #f5f5f4;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
  color: #6b6b6b;
  text-transform: capitalize;
`;

const Dot = styled.span`
  color: #d4d4d0;
`;

const ArticleBody = styled.div`
  margin-bottom: 32px;
  line-height: 1.7;
  color: #37352f;
  font-size: 15px;

  h2 {
    font-size: 16px;
    font-weight: 600;
    color: #37352f;
    margin-top: 28px;
    margin-bottom: 10px;
    display: block;
  }

  h3 {
    font-size: 14px;
    font-weight: 600;
    color: #37352f;
    margin-top: 20px;
    margin-bottom: 8px;
    display: block;
  }

  h4 {
    font-size: 14px;
    font-weight: 500;
    color: #6b6b6b;
    margin-top: 16px;
    margin-bottom: 6px;
  }

  p {
    margin-bottom: 14px;
  }

  ul, ol {
    margin-bottom: 14px;
    padding-left: 24px;
  }

  li {
    margin-bottom: 4px;
    line-height: 1.6;
  }

  blockquote {
    border-left: 3px solid #e8e8e6;
    padding-left: 16px;
    margin: 20px 0;
    color: #6b6b6b;
    font-style: italic;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 13px;
  }

  th, td {
    padding: 8px 12px;
    border: 1px solid #e8e8e6;
    text-align: left;
  }

  th {
    background: #f8f8f7;
    font-weight: 500;
    color: #37352f;
  }

  code {
    font-size: 13px;
    background: #f5f5f4;
    padding: 2px 5px;
    border-radius: 3px;
    color: #c7254e;
  }

  pre {
    background: #f8f8f7;
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 20px 0;
    border: 1px solid #e8e8e6;
  }

  pre code {
    background: none;
    padding: 0;
    color: #37352f;
  }

  a {
    color: #0080ff;
    text-decoration: none;
    border-bottom: 1px solid #0080ff40;
    transition: border-color 0.15s ease;

    &:hover {
      border-color: #0080ff;
    }
  }

  a.wikilink {
    border-bottom-style: dotted;
    border-color: #0080ff60;

    &:hover {
      border-bottom-style: solid;
      border-color: #0080ff;
    }
  }

  a::before, a::after {
    display: none !important;
  }
`;

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

interface WikiArticleViewProps {
  article: WikiArticle;
}

function stripLeadingH1(html: string): string {
  return html.replace(/^\s*<h1[^>]*>.*?<\/h1>\s*/, '');
}

export default function WikiArticleView({ article }: WikiArticleViewProps) {
  const bodyHtml = stripLeadingH1(article.htmlContent);

  return (
    <article>
      <ArticleHeader>
        <ArticleTitle>{article.title}</ArticleTitle>
        <MetaRow>
          {article.type && <TypeBadge>{article.type}</TypeBadge>}
          {article.directory && (
            <>
              <Dot>/</Dot>
              <span>{article.directory}</span>
            </>
          )}
          {article.last_updated && (
            <>
              <Dot>&middot;</Dot>
              <span>{formatDate(article.last_updated)}</span>
            </>
          )}
          <Dot>&middot;</Dot>
          <span>{article.readingTime} min read</span>
        </MetaRow>
      </ArticleHeader>

      <ArticleBody dangerouslySetInnerHTML={{ __html: bodyHtml }} />
    </article>
  );
}
