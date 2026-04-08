export interface WikiArticleFrontmatter {
  title: string;
  type: string;
  created: string;
  last_updated: string;
  related?: string[];
  sources?: string[];
}

export interface WikiArticle extends WikiArticleFrontmatter {
  slug: string;
  htmlContent: string;
  backlinks: string[];
  readingTime: number;
  directory: string;
}

export interface WikiIndexEntry {
  title: string;
  slug: string;
  type: string;
  directory: string;
  created: string;
  last_updated: string;
  summary: string;
}
