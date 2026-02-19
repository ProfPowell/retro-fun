module.exports = function (eleventyConfig) {
  // Passthrough copy
  eleventyConfig.addPassthroughCopy({ "src/css": "css" });
  eleventyConfig.addPassthroughCopy({ "src/js": "js" });
  eleventyConfig.addPassthroughCopy({ "src/demos": "demos" });
  eleventyConfig.addPassthroughCopy({ "src/img": "img" });

  // Ignore demos from template processing (they are passthrough-copied)
  eleventyConfig.ignores.add("src/demos/**");

  // Filters
  eleventyConfig.addFilter("readableDate", (dateVal) => {
    const d = new Date(dateVal);
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  });

  eleventyConfig.addFilter("isoDate", (dateVal) => {
    return new Date(dateVal).toISOString().split("T")[0];
  });

  eleventyConfig.addFilter("limit", (arr, n) => {
    return arr.slice(0, n);
  });

  // Collection: everything (demos from demoMeta.json + posts), sorted newest first
  eleventyConfig.addCollection("everything", function (collectionApi) {
    const demoMeta = require("./src/_data/demoMeta.json");

    // Get posts
    const posts = collectionApi.getFilteredByTag("post").map((p) => ({
      title: p.data.title,
      description: p.data.description || "",
      date: p.date,
      url: p.url,
      preview: p.data.preview || "",
      tags: p.data.displayTags || ["Post"],
      tagTypes: p.data.tagTypes || ["post"],
      order: p.data.order || 0,
      type: "post",
    }));

    // Normalize demos
    const demos = demoMeta.map((d) => ({
      ...d,
      date: new Date(d.date + "T12:00:00Z"),
      type: "demo",
    }));

    // Merge and sort: newest first, then by order (lower = first)
    const all = [...demos, ...posts].sort((a, b) => {
      const diff = b.date - a.date;
      if (diff !== 0) return diff;
      return (a.order || 0) - (b.order || 0);
    });

    return all;
  });

  return {
    dir: {
      input: "src",
      output: "docs",
    },
    pathPrefix: "/",
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
  };
};
