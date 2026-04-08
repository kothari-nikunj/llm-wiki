import { readFileSync, readdirSync, existsSync } from 'fs';
import { join, relative, basename } from 'path';
import matter from 'gray-matter';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkRehype from 'remark-rehype';
import rehypeSlug from 'rehype-slug';
import rehypeStringify from 'rehype-stringify';
import type { WikiArticle, WikiIndexEntry } from '@/types/wiki';

const WIKI_DIR = join(process.cwd(), 'wiki');
const BACKLINKS_PATH = join(WIKI_DIR, '_backlinks.json');

function toDateString(val: unknown): string {
  if (!val) return '';
  if (val instanceof Date) return val.toISOString().split('T')[0];
  return String(val);
}

const SKIP_FILES = new Set(['_index.md', '_backlinks.json', '_absorb_log.json']);

function getWikiFiles(dir: string): string[] {
  if (!existsSync(dir)) return [];
  const files: string[] = [];

  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || entry.name.startsWith('_')) continue;
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...getWikiFiles(fullPath));
    } else if (entry.name.endsWith('.md') && !SKIP_FILES.has(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

function filePathToSlug(filePath: string): string {
  const rel = relative(WIKI_DIR, filePath);
  return rel.replace(/\.md$/, '');
}

function slugToFilePath(slug: string): string {
  return join(WIKI_DIR, `${slug}.md`);
}

function transformWikilinks(markdown: string): string {
  return markdown.replace(/\[\[([^\]]+)\]\]/g, (_match, link: string) => {
    const parts = link.split('|');
    const slug = parts[0].trim().toLowerCase().replace(/\s+/g, '-');
    const label = parts.length > 1 ? parts[1].trim() : parts[0].trim();
    return `<a href="/wiki/${slug}" class="wikilink">${label}</a>`;
  });
}

async function compileMarkdown(content: string): Promise<string> {
  const transformed = transformWikilinks(content);

  const result = await unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeSlug)
    .use(rehypeStringify, { allowDangerousHtml: true })
    .process(transformed);

  return String(result);
}

function estimateReadingTime(content: string): number {
  const words = content.split(/\s+/).length;
  return Math.max(1, Math.ceil(words / 250));
}

function extractSummary(content: string): string {
  const lines = content.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('---')) {
      let clean = trimmed.replace(/\[\[([^\]]*?\|)?([^\]]+)\]\]/g, '$2');
      clean = clean.length > 120 ? clean.slice(0, 117) + '...' : clean;
      return clean;
    }
  }
  return '';
}

export function getArticleSlugs(): string[] {
  return getWikiFiles(WIKI_DIR).map(filePathToSlug);
}

export async function getArticleBySlug(slug: string): Promise<WikiArticle | null> {
  const filePath = slugToFilePath(slug);
  if (!existsSync(filePath)) return null;

  const raw = readFileSync(filePath, 'utf8');
  const { data, content } = matter(raw);
  const htmlContent = await compileMarkdown(content);
  const backlinks = getBacklinks(slug);
  const parts = slug.split('/');
  const directory = parts.length > 1 ? parts[0] : '';

  return {
    title: data.title || basename(slug),
    type: data.type || 'article',
    created: toDateString(data.created),
    last_updated: toDateString(data.last_updated),
    related: data.related || [],
    sources: data.sources || [],
    slug,
    htmlContent,
    backlinks,
    readingTime: estimateReadingTime(content),
    directory,
  };
}

export function getAllArticles(): WikiIndexEntry[] {
  const files = getWikiFiles(WIKI_DIR);
  const articles: WikiIndexEntry[] = [];

  for (const filePath of files) {
    const raw = readFileSync(filePath, 'utf8');
    const { data, content } = matter(raw);
    const slug = filePathToSlug(filePath);
    const parts = slug.split('/');

    articles.push({
      title: data.title || basename(slug),
      slug,
      type: data.type || 'article',
      directory: parts.length > 1 ? parts[0] : '',
      created: toDateString(data.created),
      last_updated: toDateString(data.last_updated),
      summary: extractSummary(content),
    });
  }

  articles.sort((a, b) => {
    if (!a.last_updated) return 1;
    if (!b.last_updated) return -1;
    return b.last_updated.localeCompare(a.last_updated);
  });

  return articles;
}

export function getBacklinks(slug: string): string[] {
  if (!existsSync(BACKLINKS_PATH)) return [];
  try {
    const data = JSON.parse(readFileSync(BACKLINKS_PATH, 'utf8'));
    return data[slug] || [];
  } catch {
    return [];
  }
}

export function getDirectories(): string[] {
  if (!existsSync(WIKI_DIR)) return [];
  return readdirSync(WIKI_DIR, { withFileTypes: true })
    .filter(e => e.isDirectory() && !e.name.startsWith('.') && !e.name.startsWith('_'))
    .map(e => e.name)
    .sort();
}
