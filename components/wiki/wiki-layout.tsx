import Link from 'next/link';
import { useRouter } from 'next/router';
import styled from 'styled-components';
import { ReactNode, useState, useMemo } from 'react';
import type { WikiIndexEntry } from '@/types/wiki';

const Shell = styled.div`
  display: flex;
  min-height: 100vh;

  @media (max-width: 768px) {
    flex-direction: column;
  }
`;

const Sidebar = styled.aside`
  width: 260px;
  min-width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100dvh;
  overflow-y: auto;
  overflow-x: hidden;
  background: #fff;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }

  @media (max-width: 768px) {
    width: 100%;
    min-width: 100%;
    height: auto;
    position: static;
    border-right: none;
    border-bottom: 1px solid #eee;
  }
`;

const SidebarHeader = styled.div`
  padding: 20px 20px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const SidebarTitle = styled.a`
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  text-decoration: none;
`;

const ShuffleBtn = styled.button`
  font-size: 14px;
  background: none;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 2px 8px;
  cursor: pointer;
  color: #c4c4c0;
  font-family: inherit;
  transition: border-color 0.12s ease, color 0.12s ease;
  display: flex;
  align-items: center;
  line-height: 1;

  &:hover {
    border-color: #ccc;
    color: #1a1a1a;
  }
`;

const SidebarSearch = styled.input`
  width: calc(100% - 40px);
  margin: 0 20px 16px;
  padding: 7px 12px;
  font-size: 13px;
  font-family: inherit;
  border: 1px solid #eee;
  border-radius: 6px;
  outline: none;

  &:focus {
    border-color: #0080ff;
  }

  &::placeholder {
    color: #c4c4c0;
  }
`;

const CategoryGroup = styled.div`
  margin-bottom: 8px;
`;

const CategoryHeader = styled.button`
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  font-size: 14px;
  font-family: inherit;
  font-weight: 600;
  color: #1a1a1a;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.08s ease;

  &:hover {
    background: #f8f8f7;
  }
`;

const Arrow = styled.span`
  font-size: 10px;
  color: #b0b0ac;
  width: 12px;
  flex-shrink: 0;
`;

const Count = styled.span`
  font-size: 10px;
  color: #c4c4c0;
  margin-left: auto;
`;

const CategoryItems = styled.div<{ $collapsed: boolean }>`
  display: ${(p) => (p.$collapsed ? 'none' : 'flex')};
  flex-direction: column;
`;

const SidebarLink = styled.a<{ $active?: boolean }>`
  display: block !important;
  font-size: 13px;
  color: ${(p) => (p.$active ? '#0080ff' : '#6b6b6b')};
  font-weight: ${(p) => (p.$active ? '500' : '400')};
  padding: 4px 20px 4px 44px !important;
  text-decoration: none;
  transition: color 0.08s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  &:hover {
    color: #1a1a1a;
    background: #f8f8f7;
  }
`;

const MainContent = styled.main`
  flex: 1;
  min-width: 0;
  padding: 32px 48px 80px;

  @media (max-width: 768px) {
    padding: 20px 16px 40px;
  }
`;

interface WikiLayoutProps {
  children: ReactNode;
  articles?: WikiIndexEntry[];
  isIndex?: boolean;
}

export default function WikiLayout({ children, articles = [], isIndex }: WikiLayoutProps) {
  const router = useRouter();
  const currentSlug = router.asPath.replace('/wiki/', '');
  const [query, setQuery] = useState('');

  const directories = useMemo(() => {
    const dirs = new Set<string>();
    for (const a of articles) {
      if (a.directory) dirs.add(a.directory);
    }
    return Array.from(dirs).sort().map((d) => ({
      slug: d,
      label: d.charAt(0).toUpperCase() + d.slice(1),
    }));
  }, [articles]);

  const activeDir = useMemo(() => {
    if (isIndex) return '';
    const match = articles.find((a) => currentSlug === a.slug);
    return match?.directory || '';
  }, [isIndex, currentSlug, articles]);

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    if (isIndex) {
      return Object.fromEntries(directories.map((c, i) => [c.slug, i !== 0]));
    }
    return Object.fromEntries(
      directories.map((c) => [c.slug, c.slug !== activeDir])
    );
  });

  const filteredArticles = query
    ? articles.filter(
        (a) =>
          a.title.toLowerCase().includes(query.toLowerCase()) ||
          a.directory.toLowerCase().includes(query.toLowerCase())
      )
    : articles;

  const grouped = directories.map((cat) => ({
    ...cat,
    items: filteredArticles
      .filter((a) => a.directory === cat.slug)
      .sort((a, b) => a.title.localeCompare(b.title)),
  })).filter((cat) => cat.items.length > 0);

  function toggleCategory(slug: string) {
    setCollapsed((prev) => ({ ...prev, [slug]: !prev[slug] }));
  }

  function goToRandom() {
    if (articles.length === 0) return;
    const random = articles[Math.floor(Math.random() * articles.length)];
    router.push(`/wiki/${random.slug}`);
  }

  return (
    <Shell className="wiki-page">
      <Sidebar>
        <SidebarHeader>
          <Link href="/wiki" passHref legacyBehavior>
            <SidebarTitle>Wiki</SidebarTitle>
          </Link>
          <ShuffleBtn onClick={goToRandom} title="Random article">Random</ShuffleBtn>
        </SidebarHeader>
        <SidebarSearch
          type="text"
          placeholder="Search articles..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {grouped.map((cat) => (
          <CategoryGroup key={cat.slug}>
            <CategoryHeader onClick={() => toggleCategory(cat.slug)}>
              <Arrow>{collapsed[cat.slug] ? '\u25B8' : '\u25BE'}</Arrow>
              {cat.label}
              <Count>{cat.items.length}</Count>
            </CategoryHeader>
            <CategoryItems $collapsed={!!collapsed[cat.slug]}>
              {cat.items.map((item) => (
                <Link key={item.slug} href={`/wiki/${item.slug}`} passHref legacyBehavior>
                  <SidebarLink $active={currentSlug === item.slug}>
                    {item.title}
                  </SidebarLink>
                </Link>
              ))}
            </CategoryItems>
          </CategoryGroup>
        ))}
      </Sidebar>
      <MainContent>{children}</MainContent>
    </Shell>
  );
}
