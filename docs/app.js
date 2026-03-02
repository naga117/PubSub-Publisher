(function () {
  const statusLine = document.getElementById("statusLine");
  const totalReleasesEl = document.getElementById("totalReleases");
  const totalDownloadsEl = document.getElementById("totalDownloads");
  const latestVersionEl = document.getElementById("latestVersion");
  const latestPublishedEl = document.getElementById("latestPublished");
  const releaseListEl = document.getElementById("releaseList");
  const refreshButton = document.getElementById("refreshButton");
  const latestDownloadLinkEl = document.getElementById("latestDownloadLink");
  const githubReleasesLinkEl = document.getElementById("githubReleasesLink");
  const repoLineEl = document.getElementById("repoLine");
  const discussionsLinkEl = document.getElementById("discussionsLink");
  const reviewsHintEl = document.getElementById("reviewsHint");
  const giscusHostEl = document.getElementById("giscusHost");

  const fallbackConfig = {
    owner: "",
    repo: "",
    releasesPerPage: 30,
    giscus: {
      enabled: false,
      repo: "",
      repoId: "",
      category: "General",
      categoryId: "",
      mapping: "pathname",
      term: "",
      theme: "light",
      lang: "en",
    },
  };

  const userConfig = window.PUBSUB_SITE_CONFIG || {};
  const config = {
    ...fallbackConfig,
    ...userConfig,
    giscus: {
      ...fallbackConfig.giscus,
      ...(userConfig.giscus || {}),
    },
  };

  function setStatus(message, isError) {
    statusLine.textContent = message;
    statusLine.classList.toggle("error", Boolean(isError));
  }

  function deriveRepoFromLocation() {
    const hostnameParts = window.location.hostname.split(".");
    if (hostnameParts.length < 3) {
      return { owner: "", repo: "" };
    }
    if (hostnameParts[1] !== "github" || hostnameParts[2] !== "io") {
      return { owner: "", repo: "" };
    }

    const owner = hostnameParts[0];
    const pathParts = window.location.pathname.split("/").filter(Boolean);
    const repo = pathParts.length > 0 ? pathParts[0] : "";
    return { owner, repo };
  }

  function resolveRepo() {
    if (config.owner && config.repo) {
      return { owner: config.owner, repo: config.repo };
    }
    return deriveRepoFromLocation();
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("en-US");
  }

  function formatDate(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return "-";
    return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "2-digit" });
  }

  function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function markdownToHtml(markdown) {
    if (!markdown || !markdown.trim()) {
      return "<p>No changelog notes found for this release.</p>";
    }

    const lines = markdown.split("\n");
    const html = [];
    let inList = false;

    function closeList() {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
    }

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        closeList();
        continue;
      }

      if (trimmed.startsWith("### ")) {
        closeList();
        html.push(`<h4>${escapeHtml(trimmed.slice(4))}</h4>`);
        continue;
      }

      if (trimmed.startsWith("## ")) {
        closeList();
        html.push(`<h4>${escapeHtml(trimmed.slice(3))}</h4>`);
        continue;
      }

      if (trimmed.startsWith("- ")) {
        if (!inList) {
          html.push("<ul>");
          inList = true;
        }
        html.push(`<li>${escapeHtml(trimmed.slice(2))}</li>`);
        continue;
      }

      closeList();
      html.push(`<p>${escapeHtml(trimmed)}</p>`);
    }

    closeList();
    return html.join("");
  }

  function pickLatestAsset(release) {
    if (!release || !Array.isArray(release.assets) || release.assets.length === 0) {
      return null;
    }

    const zipAsset = release.assets.find((asset) => asset.name.toLowerCase().endsWith(".zip"));
    return zipAsset || release.assets[0];
  }

  function releaseDownloadTotal(release) {
    return (release.assets || []).reduce((sum, asset) => sum + Number(asset.download_count || 0), 0);
  }

  function renderStats(releases) {
    const latest = releases[0];
    const totalDownloads = releases.reduce((sum, release) => sum + releaseDownloadTotal(release), 0);

    totalReleasesEl.textContent = formatNumber(releases.length);
    totalDownloadsEl.textContent = formatNumber(totalDownloads);
    latestVersionEl.textContent = latest ? latest.tag_name || latest.name || "-" : "-";
    latestPublishedEl.textContent = latest ? formatDate(latest.published_at) : "-";

    const latestAsset = pickLatestAsset(latest);
    if (latestAsset) {
      latestDownloadLinkEl.href = latestAsset.browser_download_url;
      latestDownloadLinkEl.textContent = `Download ${latestAsset.name}`;
      latestDownloadLinkEl.removeAttribute("aria-disabled");
    } else {
      latestDownloadLinkEl.href = "#";
      latestDownloadLinkEl.textContent = "No build asset found";
      latestDownloadLinkEl.setAttribute("aria-disabled", "true");
    }
  }

  function renderReleases(releases) {
    if (!releases.length) {
      releaseListEl.innerHTML = '<p class="empty">No releases found yet.</p>';
      return;
    }

    const cards = releases.map((release) => {
      const badges = [];
      if (release.prerelease) badges.push('<span class="badge">Pre-release</span>');
      if (release.draft) badges.push('<span class="badge">Draft</span>');

      const assets = Array.isArray(release.assets) ? release.assets : [];
      const assetsHtml = assets.length
        ? `<ul class="asset-list">${assets
            .map(
              (asset) => `
                <li>
                  <div>
                    <a href="${asset.browser_download_url}" target="_blank" rel="noopener noreferrer">${escapeHtml(asset.name)}</a>
                    <p class="asset-meta">${formatBytes(asset.size)} | ${formatNumber(asset.download_count)} downloads</p>
                  </div>
                  <a href="${asset.browser_download_url}" target="_blank" rel="noopener noreferrer">Download</a>
                </li>`
            )
            .join("")}</ul>`
        : '<p class="empty">No downloadable files attached to this release.</p>';

      return `
        <article class="release-card">
          <div class="release-head">
            <h3>${escapeHtml(release.name || release.tag_name)}</h3>
            <div>${badges.join(" ")}</div>
          </div>
          <p class="meta">
            ${escapeHtml(release.tag_name)} | Published ${formatDate(release.published_at)} | ${formatNumber(
              releaseDownloadTotal(release)
            )} downloads
          </p>
          ${assetsHtml}
          <details class="release-notes">
            <summary>View changelog</summary>
            <div class="notes-content">${markdownToHtml(release.body)}</div>
          </details>
        </article>`;
    });

    releaseListEl.innerHTML = cards.join("");
  }

  function configureReviewSection(owner, repo) {
    reviewsHintEl.classList.remove("error");
    discussionsLinkEl.href = `https://github.com/${owner}/${repo}/discussions`;
    const giscus = config.giscus || {};
    const giscusRepo = giscus.repo || `${owner}/${repo}`;

    if (!giscus.enabled) {
      reviewsHintEl.textContent =
        "Enable GitHub Discussions and set giscus IDs in docs/site-config.js to collect public reviews here.";
      return;
    }

    if (!giscus.repoId || !giscus.categoryId) {
      reviewsHintEl.textContent =
        "giscus is enabled but repoId/categoryId are missing in docs/site-config.js. Fill these values from giscus.app.";
      reviewsHintEl.classList.add("error");
      return;
    }

    reviewsHintEl.textContent = "Reviews are powered by GitHub Discussions.";

    const script = document.createElement("script");
    script.src = "https://giscus.app/client.js";
    script.async = true;
    script.crossOrigin = "anonymous";
    script.setAttribute("data-repo", giscusRepo);
    script.setAttribute("data-repo-id", giscus.repoId);
    script.setAttribute("data-category", giscus.category || "General");
    script.setAttribute("data-category-id", giscus.categoryId);
    script.setAttribute("data-mapping", giscus.mapping || "pathname");
    script.setAttribute("data-term", giscus.term || "");
    script.setAttribute("data-strict", "0");
    script.setAttribute("data-reactions-enabled", "1");
    script.setAttribute("data-emit-metadata", "0");
    script.setAttribute("data-input-position", "top");
    script.setAttribute("data-theme", giscus.theme || "light");
    script.setAttribute("data-lang", giscus.lang || "en");
    giscusHostEl.innerHTML = "";
    giscusHostEl.appendChild(script);
  }

  async function loadReleases() {
    const { owner, repo } = resolveRepo();
    if (!owner || !repo) {
      setStatus(
        "Repository owner/name could not be resolved. Update docs/site-config.js with owner and repo values.",
        true
      );
      releaseListEl.innerHTML = '<p class="empty">Cannot fetch releases until the repo is configured.</p>';
      return;
    }

    const releasesUrl = `https://github.com/${owner}/${repo}/releases`;
    const releasesApiUrl = `https://api.github.com/repos/${owner}/${repo}/releases?per_page=${Number(
      config.releasesPerPage || 30
    )}`;

    repoLineEl.textContent = `Repository: ${owner}/${repo}`;
    githubReleasesLinkEl.href = releasesUrl;
    configureReviewSection(owner, repo);
    setStatus("Loading releases from GitHub API...");

    try {
      const response = await fetch(releasesApiUrl, {
        headers: {
          Accept: "application/vnd.github+json",
        },
      });

      if (!response.ok) {
        throw new Error(`GitHub API returned ${response.status}`);
      }

      const releases = await response.json();
      const publishedReleases = releases.filter((release) => !release.draft);

      renderStats(publishedReleases);
      renderReleases(publishedReleases);
      setStatus(`Loaded ${publishedReleases.length} releases from GitHub.`);
    } catch (error) {
      console.error(error);
      setStatus(
        "Failed to load release data. GitHub API may be rate-limited or unavailable right now. Try again shortly.",
        true
      );
      releaseListEl.innerHTML =
        '<p class="empty">Release data is temporarily unavailable. Check the GitHub Releases page directly.</p>';
    }
  }

  refreshButton.addEventListener("click", function () {
    loadReleases();
  });

  loadReleases();
})();
