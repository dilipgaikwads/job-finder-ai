"use strict";

(function () {
  var state = {
    userId: sessionStorage.getItem("jf_user_id") || "",
    token: sessionStorage.getItem("jf_token") || "",
    profile: null,
    lastSearch: null
  };

  var pageTitles = {
    dashboard: "Overview",
    profile: "My profile",
    discover: "Find jobs",
    alerts: "Notifications"
  };

  function byId(id) { return document.getElementById(id); }
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function safeUrl(value) {
    try {
      var url = new URL(value);
      return (url.protocol === "https:" || url.protocol === "http:") ? url.href : "";
    } catch (error) { return ""; }
  }
  function showToast(message) {
    var toast = byId("toast");
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(function () { toast.classList.remove("show"); }, 4200);
  }
  function setMessage(id, message, isError) {
    var node = byId(id);
    node.textContent = message;
    node.hidden = false;
    node.classList.toggle("error", !!isError);
  }
  function clearMessage(id) {
    var node = byId(id);
    node.hidden = true;
    node.textContent = "";
    node.classList.remove("error");
  }
  function authHeaders() {
    return state.token ? { "Authorization": "Bearer " + state.token } : {};
  }
  async function api(path, options) {
    options = options || {};
    var headers = Object.assign({}, options.headers || {});
    if (options.auth !== false && state.token) {
      headers.Authorization = "Bearer " + state.token;
    }
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    var response;
    try {
      response = await fetch(path, {
        method: options.method || "GET",
        headers: headers,
        body: options.body
      });
    } catch (error) {
      throw new Error("Cannot reach the local backend. Check that Uvicorn is running on port 8000.");
    }
    var body = null;
    var text = await response.text();
    if (text) {
      try { body = JSON.parse(text); } catch (error) { body = { detail: text }; }
    }
    if (!response.ok) {
      var detail = body && body.detail;
      if (response.status === 401) {
        clearSession();
        throw new Error("Your local session has expired. Upload your resume again to create a new session.");
      }
      if (typeof detail === "string") throw new Error(detail);
      if (detail && Array.isArray(detail)) throw new Error(detail.map(function (item) { return item.msg || JSON.stringify(item); }).join("; "));
      throw new Error("Request failed (" + response.status + "). " + (detail ? JSON.stringify(detail) : ""));
    }
    return body;
  }
  function clearSession() {
    state.userId = "";
    state.token = "";
    state.profile = null;
    sessionStorage.removeItem("jf_user_id");
    sessionStorage.removeItem("jf_token");
    sessionStorage.removeItem("jf_profile");
    updateSessionUI();
    renderProfile(null);
  }
  function persistSession(data) {
    state.userId = data.user_id;
    state.token = data.token;
    state.profile = data;
    sessionStorage.setItem("jf_user_id", state.userId);
    sessionStorage.setItem("jf_token", state.token);
    sessionStorage.setItem("jf_profile", JSON.stringify(data));
    updateSessionUI();
    renderProfile(data);
  }
  function updateSessionUI() {
    var connected = !!(state.userId && state.token);
    byId("sidebarUser").textContent = state.profile && state.profile.detected_name ? state.profile.detected_name : (connected ? "Your profile" : "Your workspace");
    byId("sidebarSession").textContent = connected ? "Profile session active" : "Not connected";
    byId("profileSaveHint").textContent = connected ? "Your changes are saved to this local session." : "Upload a resume first to create a session.";
    byId("searchHint").textContent = connected ? "Ready to search using your active profile." : "Upload your resume and confirm your profile before searching.";
    byId("searchButton").disabled = !connected;
    byId("searchButton").style.opacity = connected ? "1" : ".55";
    byId("disconnectBtn").style.visibility = connected ? "visible" : "hidden";
    byId("metricProfile").textContent = connected ? "Active" : "Not set up";
    byId("metricProfileHint").textContent = connected ? "Resume processed in this session" : "Upload a resume to begin";
    byId("stepOne").classList.toggle("done", connected);
    byId("stepTwo").classList.toggle("done", connected);
    byId("stepOne").textContent = connected ? "✓" : "1";
    byId("stepTwo").textContent = connected ? "✓" : "2";
  }
  function renderProfile(data) {
    var empty = byId("emptyProfile");
    var extracted = byId("extractedProfile");
    if (!data) {
      empty.hidden = false;
      extracted.hidden = true;
      byId("profileStatus").textContent = "Awaiting resume";
      byId("profileStatus").classList.remove("ready");
      byId("profileName").value = "";
      byId("profileEmail").value = "";
      byId("detectedSkills").innerHTML = "";
      byId("profileGaps").innerHTML = "";
      return;
    }
    empty.hidden = true;
    extracted.hidden = false;
    byId("profileStatus").textContent = "Resume processed";
    byId("profileStatus").classList.add("ready");
    byId("detectedName").textContent = data.detected_name || "Not detected";
    byId("detectedEmail").textContent = data.detected_email || "Not detected";
    byId("detectedExperience").textContent = String(data.experience_count == null ? 0 : data.experience_count);
    byId("profileName").value = data.detected_name || "";
    byId("profileEmail").value = data.detected_email || "";
    var skills = Array.isArray(data.skills) ? data.skills : [];
    byId("detectedSkills").innerHTML = skills.length ? skills.map(function (skill) {
      return '<span class="skill-tag">' + escapeHtml(skill) + '</span>';
    }).join("") : '<span class="microcopy">No skills confidently extracted yet.</span>';
    var gaps = Array.isArray(data.gaps) ? data.gaps : [];
    byId("profileGaps").innerHTML = gaps.length ? gaps.map(function (gap) {
      return "<li>" + escapeHtml(gap) + "</li>";
    }).join("") : "<li>No outstanding questions were returned by the parser.</li>";
  }
  function switchView(view) {
    if (!pageTitles[view]) return;
    document.querySelectorAll(".view-section").forEach(function (section) {
      section.hidden = section.id !== "view-" + view;
    });
    document.querySelectorAll(".nav-item").forEach(function (button) {
      button.classList.toggle("active", button.getAttribute("data-view") === view);
    });
    byId("currentPage").textContent = pageTitles[view];
    byId("sidebar").classList.remove("open");
    if (view === "alerts") loadNotifications(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  async function checkHealth() {
    var pill = byId("connectionStatus");
    try {
      var response = await fetch("/health");
      var body = await response.json();
      if (!response.ok || body.status !== "ok") throw new Error("Backend unavailable");
      pill.classList.add("online");
      pill.classList.remove("offline");
      pill.querySelector("span").textContent = "API connected";
    } catch (error) {
      pill.classList.add("offline");
      pill.classList.remove("online");
      pill.querySelector("span").textContent = "API offline";
    }
  }
  function renderSearchResult(data) {
    state.lastSearch = data;
    byId("resultsSection").hidden = false;
    byId("resultsTimestamp").textContent = "JUST NOW";
    byId("resultsSubtitle").textContent = String(data.returned || 0) + " recommended roles from " + String(data.total_discovered || 0) + " discovered postings.";
    byId("metricJobs").textContent = String(data.total_discovered || 0);
    byId("metricMatches").textContent = String(data.returned || 0);
    byId("metricRisk").textContent = String(data.filtered_out_high_risk || 0);
    byId("stepThree").classList.add("done");
    byId("stepThree").textContent = "✓";
    byId("resultsSummary").innerHTML =
      '<span class="summary-pill"><b>' + Number(data.total_discovered || 0) + '</b> discovered</span>' +
      '<span class="summary-pill"><b>' + Number(data.returned || 0) + '</b> returned</span>' +
      '<span class="summary-pill"><b>' + Number(data.filtered_out_high_risk || 0) + '</b> high-risk filtered</span>' +
      '<span class="summary-pill"><b>' + Number(data.notifications_sent || 0) + '</b> notifications logged/sent</span>';
    var items = Array.isArray(data.items) ? data.items : [];
    if (!items.length) {
      byId("jobList").innerHTML = '<div class="panel empty-state"><span class="empty-icon">⌕</span><b>No roles were returned</b><p>Try other employer slugs or check the source errors below.</p></div>';
    } else {
      byId("jobList").innerHTML = items.map(renderJobCard).join("");
    }
    if (Array.isArray(data.errors) && data.errors.length) {
      byId("jobList").insertAdjacentHTML("beforeend", '<div class="notice-box"><span>ⓘ</span><p>Source notes: ' + escapeHtml(data.errors.join(" · ")) + '</p></div>');
    }
  }
  function renderJobCard(item) {
    var job = item.job || {};
    var status = String(item.verification_status || "unverified").toLowerCase();
    var allowed = ["verified", "partially_verified", "unverified", "high_risk"];
    if (allowed.indexOf(status) === -1) status = "unverified";
    var score = Math.max(0, Math.min(100, Math.round(Number(item.composite_match || 0) * 100)));
    var appUrl = safeUrl(item.application_url || job.application_url);
    var location = job.location || "Location not specified";
    var remote = String((job.remote_status && job.remote_status.replace(/_/g, " ")) || "unknown");
    var company = job.employer || "Employer";
    var title = job.title || "Untitled role";
    var snippet = String(job.description || "").slice(0, 420);
    var requirements = Array.isArray(job.requirements) ? job.requirements : [];
    var meta = '<span>⌖ ' + escapeHtml(location) + '</span><span>◈ ' + escapeHtml(remote) + '</span><span>▤ ' + escapeHtml(String(job.employment_type || "unknown").replace(/_/g, " ")) + '</span>';
    if (job.posted_at) meta += '<span>◷ ' + escapeHtml(String(job.posted_at).slice(0, 10)) + '</span>';
    var jobDetails = '<details class="job-details"><summary>View role details and requirements</summary><p>' + escapeHtml(snippet || "No description returned.") + '</p>' +
      (requirements.length ? '<p><b>Requirements:</b> ' + escapeHtml(requirements.join(" · ")) + '</p>' : "") + '</details>';
    var action = appUrl ? '<a href="' + escapeHtml(appUrl) + '" target="_blank" rel="noopener noreferrer">View application ↗</a>' : '<span class="microcopy">Application link unavailable</span>';
    var summary = item.match_summary || "Review the role and compare its requirements with your experience.";
    var risk = Array.isArray(item.risk_flags) && item.risk_flags.length ? '<div class="job-details"><b>Risk indicators:</b> ' + escapeHtml(item.risk_flags.join(", ")) + '</div>' : "";
    return '<article class="job-card"><div class="job-card-top"><div class="job-heading"><span class="company-avatar">' + escapeHtml(company.slice(0, 1).toUpperCase()) + '</span><div><h3>' + escapeHtml(title) + '</h3><p>' + escapeHtml(company) + '</p></div></div><div class="job-badges"><span class="verification-badge ' + status + '">' + escapeHtml(status.replace(/_/g, " ")) + '</span></div></div><div class="job-meta">' + meta + '</div><div class="job-bottom"><div class="match-score"><span class="score-number">' + score + '<small>% match</small></span><span class="match-description">' + escapeHtml(summary) + '</span></div><div class="job-actions">' + action + '</div></div>' + jobDetails + risk + '</article>';
  }
  async function loadNotifications(showFeedback) {
    if (!state.token || !state.userId) {
      byId("notificationList").innerHTML = '<div class="empty-state"><span class="empty-icon">◷</span><b>Connect your profile first</b><p>Upload your resume to create a local session and inspect notifications.</p></div>';
      if (showFeedback) showToast("Upload a resume before checking notifications.");
      return;
    }
    try {
      var data = await api("/notifications/" + encodeURIComponent(state.userId));
      var items = Array.isArray(data.notifications) ? data.notifications : [];
      if (!items.length) {
        byId("notificationList").innerHTML = '<div class="empty-state"><span class="empty-icon">◷</span><b>No notifications yet</b><p>Verified matches can be logged during a search when notifications are enabled.</p></div>';
      } else {
        byId("notificationList").innerHTML = items.map(function (item) {
          return '<div class="notification-item"><span class="notification-icon">✓</span><div><b>' + escapeHtml(item.subject || "Job match alert") + '</b><p>Job reference: ' + escapeHtml(item.job_id || "—") + '</p><small>' + escapeHtml(item.created_at || "") + '</small></div></div>';
        }).join("");
      }
      if (showFeedback) showToast("Notifications refreshed.");
    } catch (error) {
      byId("notificationList").innerHTML = '<div class="empty-state"><span class="empty-icon">ⓘ</span><b>Notification records unavailable</b><p>' + escapeHtml(error.message) + '</p></div>';
      if (showFeedback) showToast(error.message);
    }
  }

  document.querySelectorAll("[data-view]").forEach(function (button) {
    button.addEventListener("click", function () { switchView(button.getAttribute("data-view")); });
  });
  document.querySelectorAll("[data-go]").forEach(function (button) {
    button.addEventListener("click", function () { switchView(button.getAttribute("data-go")); });
  });
  byId("menuBtn").addEventListener("click", function () { byId("sidebar").classList.toggle("open"); });
  byId("disconnectBtn").addEventListener("click", function () {
    if (window.confirm("Clear this browser's Job Finder AI session? The backend profile remains until the server restarts.")) {
      clearSession();
      showToast("Browser session cleared.");
    }
  });
  byId("resumeFile").addEventListener("change", function (event) {
    var file = event.target.files && event.target.files[0];
    byId("selectedFile").textContent = file ? file.name + " · " + Math.ceil(file.size / 1024) + " KB" : "No file selected";
  });
  var dropzone = byId("dropzone");
  ["dragenter", "dragover"].forEach(function (eventName) {
    dropzone.addEventListener(eventName, function (event) { event.preventDefault(); dropzone.classList.add("dragover"); });
  });
  ["dragleave", "drop"].forEach(function (eventName) {
    dropzone.addEventListener(eventName, function (event) { event.preventDefault(); dropzone.classList.remove("dragover"); });
  });
  dropzone.addEventListener("drop", function (event) {
    var files = event.dataTransfer && event.dataTransfer.files;
    if (files && files.length) {
      byId("resumeFile").files = files;
      byId("resumeFile").dispatchEvent(new Event("change"));
    }
  });
  byId("uploadForm").addEventListener("submit", async function (event) {
    event.preventDefault();
    clearMessage("uploadMessage");
    var fileInput = byId("resumeFile");
    var file = fileInput.files && fileInput.files[0];
    if (!file) { setMessage("uploadMessage", "Choose a resume file first.", true); return; }
    if (file.size > 4 * 1024 * 1024) { setMessage("uploadMessage", "The file exceeds the 4 MB upload limit.", true); return; }
    var button = byId("uploadButton");
    button.disabled = true; button.textContent = "Analysing resume…";
    try {
      var formData = new FormData();
      formData.append("file", file);
      var data = await api("/resumes", { method: "POST", body: formData, auth: false });
      persistSession(data);
      setMessage("uploadMessage", "Resume processed. Review the extracted details and confirm your preferences below.", false);
      showToast("Resume analysed successfully.");
      switchView("profile");
    } catch (error) {
      setMessage("uploadMessage", error.message, true);
    } finally {
      button.disabled = false; button.innerHTML = 'Upload and analyse <span>→</span>';
    }
  });
  byId("profileForm").addEventListener("submit", async function (event) {
    event.preventDefault();
    if (!state.token || !state.userId) { showToast("Upload your resume before saving profile preferences."); return; }
    var body = {
      full_name: byId("profileName").value.trim() || null,
      email: byId("profileEmail").value.trim() || null,
      remote_only: byId("remoteOnly").checked,
      hybrid_ok: byId("hybridOk").checked,
      onsite_ok: byId("onsiteOk").checked,
      open_to_relocation: byId("relocationOk").checked,
      open_to_international: byId("internationalOk").checked,
      min_base_salary_usd: byId("minSalary").value ? Number(byId("minSalary").value) : null,
      target_base_salary_usd: byId("targetSalary").value ? Number(byId("targetSalary").value) : null,
      role_interests: byId("roleInterests").value.split(",").map(function (s) { return s.trim(); }).filter(Boolean)
    };
    try {
      await api("/profiles/" + encodeURIComponent(state.userId), { method: "PATCH", body: JSON.stringify(body) });
      if (state.profile) {
        state.profile.detected_name = body.full_name || state.profile.detected_name;
        state.profile.detected_email = body.email || state.profile.detected_email;
        sessionStorage.setItem("jf_profile", JSON.stringify(state.profile));
      }
      updateSessionUI();
      showToast("Profile preferences saved.");
    } catch (error) { showToast("Could not save profile: " + error.message); }
  });
  byId("addCompany").addEventListener("click", function () {
    if (byId("companyList").querySelectorAll("[data-company-row]").length >= 25) {
      showToast("The API accepts up to 25 employer targets per search."); return;
    }
    var row = document.createElement("div");
    row.className = "company-row";
    row.setAttribute("data-company-row", "");
    row.innerHTML = '<label><span>Source</span><select name="adapter"><option value="greenhouse">Greenhouse</option><option value="lever">Lever</option></select></label><label class="slug-field"><span>Employer slug</span><input name="slug" placeholder="company-board-slug" required></label><button class="remove-company" type="button" aria-label="Remove company">×</button>';
    byId("companyList").appendChild(row);
  });
  byId("companyList").addEventListener("click", function (event) {
    var button = event.target.closest(".remove-company");
    if (button) {
      var rows = byId("companyList").querySelectorAll("[data-company-row]");
      if (rows.length <= 1) { showToast("Keep at least one employer target."); return; }
      button.closest("[data-company-row]").remove();
    }
  });
  byId("searchButton").addEventListener("click", async function () {
    if (!state.token || !state.userId) { showToast("Upload your resume before searching."); return; }
    var rows = Array.from(byId("companyList").querySelectorAll("[data-company-row]"));
    var targets = rows.map(function (row) {
      return {
        adapter: row.querySelector('[name="adapter"]').value,
        employer_slug: row.querySelector('[name="slug"]').value.trim()
      };
    }).filter(function (target) { return target.employer_slug.length > 0; });
    if (!targets.length) { showToast("Add at least one employer slug."); return; }
    var invalid = targets.find(function (target) { return !/^[A-Za-z0-9_-]{1,100}$/.test(target.employer_slug); });
    if (invalid) { showToast("Employer slugs can contain letters, numbers, underscores and hyphens only."); return; }
    var button = byId("searchButton");
    button.disabled = true; button.textContent = "Discovering and matching…";
    try {
      var data = await api("/profiles/" + encodeURIComponent(state.userId) + "/search", {
        method: "POST",
        body: JSON.stringify({
          targets: targets,
          top_n: Number(byId("topN").value),
          notify: byId("notifyToggle").checked
        })
      });
      renderSearchResult(data);
      switchView("discover");
      byId("resultsSection").scrollIntoView({ behavior: "smooth", block: "start" });
      showToast("Job discovery completed.");
    } catch (error) {
      showToast("Search failed: " + error.message);
    } finally {
      button.disabled = false; button.innerHTML = '<span>⌕</span> Search and match jobs';
    }
  });
  byId("refreshAlerts").addEventListener("click", function () { loadNotifications(true); });
  window.addEventListener("storage", function () { checkHealth(); });

  var storedProfile = sessionStorage.getItem("jf_profile");
  if (storedProfile) {
    try { state.profile = JSON.parse(storedProfile); renderProfile(state.profile); } catch (error) { state.profile = null; }
  }
  updateSessionUI();
  checkHealth();
})();