import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import styled from 'styled-components';
import type { WikiArticle } from '@/types/wiki';

interface TocItem {
  id: string;
  text: string;
  level: number;
}

const MarginColumn = styled.aside`
  font-size: 12px;
  color: #9b9a97;
  line-height: 1.5;
  position: relative;

  @media (max-width: 1100px) {
    margin-top: 32px;
    border-top: 1px solid #eee;
    padding-top: 20px;
  }
`;

const MarginSticky = styled.div`
  position: fixed;
  width: 180px;
  top: 50%;
  transform: translateY(-50%);
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }

  @media (max-width: 1100px) {
    position: static;
    width: auto;
    max-height: none;
  }
`;

const MarginSection = styled.div`
  margin-bottom: 20px;
`;

const MarginTitle = styled.div`
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #c4c4c0;
  margin-bottom: 6px;
`;

const TocLink = styled.a<{ $active: boolean }>`
  display: block !important;
  color: ${(p) => (p.$active ? '#1a1a1a' : '#c4c4c0')};
  text-decoration: none;
  padding: 2px 0;
  font-size: 11px;
  line-height: 1.5;
  transition: color 0.1s ease;
  cursor: pointer;

  &:hover {
    color: #1a1a1a;
  }
`;

const MarginLink = styled.a`
  display: block !important;
  color: #6b6b6b;
  text-decoration: none;
  padding: 2px 0;
  font-size: 12px;
  line-height: 1.5;
  transition: color 0.1s ease;

  &::before,
  &::after {
    display: none !important;
  }

  &:hover {
    color: #0080ff;
  }
`;

function extractHeadings(html: string): TocItem[] {
  const headings: TocItem[] = [];
  const regex = /<h([23])\s+id="([^"]*)"[^>]*>([^<]*)<\/h[23]>/g;
  let match;
  while ((match = regex.exec(html)) !== null) {
    headings.push({
      id: match[2],
      text: match[3],
      level: parseInt(match[1], 10),
    });
  }
  return headings;
}

function parseWikilink(link: string): { slug: string; label: string } {
  const cleaned = link.replace(/\[\[|\]\]/g, '');
  const parts = cleaned.split('|');
  const slug = parts[0].trim().toLowerCase().replace(/\s+/g, '-');
  if (parts.length > 1) {
    return { slug, label: parts[1].trim() };
  }
  // No explicit label — derive from slug: "people/some-person" -> "Some Person"
  const name = slug.split('/').pop() || slug;
  const label = name.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return { slug, label };
}

interface WikiMarginProps {
  article: WikiArticle;
  contentRef: React.RefObject<HTMLDivElement | null>;
}

export default function WikiMargin({ article, contentRef }: WikiMarginProps) {
  const headings = extractHeadings(article.htmlContent);
  const [activeId, setActiveId] = useState('');
  const observerRef = useRef<IntersectionObserver | null>(null);
  const relatedLinks = (article.related || []).map(parseWikilink);

  useEffect(() => {
    if (!contentRef.current || headings.length === 0) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0.1 }
    );

    const elements = headings
      .map((h) => document.getElementById(h.id))
      .filter(Boolean) as HTMLElement[];

    for (const el of elements) {
      observerRef.current.observe(el);
    }

    return () => {
      observerRef.current?.disconnect();
    };
  }, [article.htmlContent]);

  const hasContent = headings.length >= 2 || relatedLinks.length > 0 || article.backlinks.length > 0;
  if (!hasContent) return null;

  return (
    <MarginColumn>
      <div style={{ height: 240 }} />
      <MarginSticky>
        {headings.length >= 2 && (
          <MarginSection>
            <MarginTitle>Contents</MarginTitle>
            {headings.map((h) => (
              <TocLink
                key={h.id}
                href={`#${h.id}`}
                $active={activeId === h.id}
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById(h.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }}
              >
                {h.text}
              </TocLink>
            ))}
          </MarginSection>
        )}

        {relatedLinks.length > 0 && (
          <MarginSection>
            <MarginTitle>Related</MarginTitle>
            {relatedLinks.map(({ slug, label }) => (
              <Link key={slug} href={`/wiki/${slug}`} passHref legacyBehavior>
                <MarginLink>{label}</MarginLink>
              </Link>
            ))}
          </MarginSection>
        )}

        {article.backlinks.length > 0 && (
          <MarginSection>
            <MarginTitle>Linked from</MarginTitle>
            {article.backlinks.map((slug) => (
              <Link key={slug} href={`/wiki/${slug}`} passHref legacyBehavior>
                <MarginLink>
                  {slug.split('/').pop()?.replace(/-/g, ' ')}
                </MarginLink>
              </Link>
            ))}
          </MarginSection>
        )}
      </MarginSticky>
    </MarginColumn>
  );
}
