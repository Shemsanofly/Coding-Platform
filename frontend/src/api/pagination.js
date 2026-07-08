/**
 * Normalize list responses that may be a plain array (legacy) or paginated envelope.
 */
export const unwrapPaginated = (data) => {
  if (Array.isArray(data)) {
    return {
      results: data,
      count: data.length,
      next: null,
      previous: null,
    };
  }
  if (data && Array.isArray(data.results)) {
    return {
      results: data.results,
      count: data.count ?? data.results.length,
      next: data.next ?? null,
      previous: data.previous ?? null,
    };
  }
  return { results: [], count: 0, next: null, previous: null };
};

/** Fetch every page from a paginated list endpoint (for admin exports, etc.). */
export const fetchAllPages = async (fetchPage, { pageSize = 100 } = {}) => {
  const all = [];
  let page = 1;

  while (true) {
    const payload = await fetchPage({ page, page_size: pageSize });
    const { results, next } = unwrapPaginated(payload);
    all.push(...results);
    if (!next) {
      break;
    }
    page += 1;
  }

  return all;
};

/** Return just the items array — uses a large page size for student-facing lists. */
export const fetchListItems = async (fetchPage, { pageSize = 100 } = {}) => {
  const payload = await fetchPage({ page: 1, page_size: pageSize });
  return unwrapPaginated(payload).results;
};
