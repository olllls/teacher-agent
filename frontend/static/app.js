document.addEventListener("DOMContentLoaded", function () {
  const pagePath = window.location.pathname;

  // ============ Upload Page ============
  if (pagePath === "/") {
    initUploadPage();
  }

  // ============ Generate Page ============
  if (pagePath.startsWith("/generate/")) {
    initGeneratePage();
  }

  // =====================================
  // Upload Page Logic
  // =====================================
  function initUploadPage() {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");
    const fileInfo = document.getElementById("fileInfo");
    const fileName = document.getElementById("fileName");
    const removeBtn = document.getElementById("removeFile");
    const submitBtn = document.getElementById("submitBtn");
    const uploadForm = document.getElementById("uploadForm");
    const previewSection = document.getElementById("previewSection");

    let selectedFile = null;

    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) {
        handleFile(fileInput.files[0]);
      }
    });

    removeBtn.addEventListener("click", () => {
      selectedFile = null;
      fileInput.value = "";
      dropzone.classList.remove("hidden");
      fileInfo.classList.add("hidden");
      submitBtn.disabled = true;
    });

    function handleFile(file) {
      const ext = file.name.split(".").pop().toLowerCase();
      if (!["xlsx", "xls"].includes(ext)) {
        alert("仅支持 .xlsx / .xls 格式");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        alert("文件大小不能超过 10MB");
        return;
      }
      selectedFile = file;
      fileName.textContent = file.name;
      dropzone.classList.add("hidden");
      fileInfo.classList.remove("hidden");
      submitBtn.disabled = false;
    }

    uploadForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      if (!selectedFile) return;

      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("class_name", document.getElementById("class_name").value.trim());
      formData.append("grade", document.getElementById("grade").value.trim());
      formData.append("semester", document.getElementById("semester").value);

      if (!formData.get("class_name")) {
        alert("请填写班级名称");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner"></span> 上传中...';

      try {
        const resp = await fetch("/api/v1/upload-excel", {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "上传失败");
        }

        const data = await resp.json();
        showPreview(data);
      } catch (err) {
        alert("上传失败: " + err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "上传并解析";
      }
    });

    function showPreview(data) {
      document.getElementById("classInfo").textContent =
        data.class_name + " | " + data.columns.join("、");
      document.getElementById("studentCount").textContent =
        "共 " + data.total + " 名学生";

      const tbody = document.getElementById("previewBody");
      tbody.innerHTML = "";
      data.preview.forEach((s, i) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${i + 1}</td>
          <td>${escHtml(s.name)}</td>
          <td>${s.score !== null ? s.score : "-"}</td>
          <td>${escHtml(s.performance || "-")}</td>
          <td>${escHtml(s.homework || "-")}</td>
        `;
        tbody.appendChild(tr);
      });

      const generateBtn = document.getElementById("generateBtn");
      generateBtn.href = "/generate/" + data.class_id;

      previewSection.classList.remove("hidden");
      previewSection.scrollIntoView({ behavior: "smooth" });

      const existing = document.querySelector(".alert-success");
      if (existing) existing.remove();
      const alert = document.createElement("div");
      alert.className = "alert alert-success";
      alert.textContent = "✅ 成功解析 " + data.total + " 名学生数据！";
      uploadForm.prepend(alert);
    }
  }

  // =====================================
  // Generate Page Logic
  // =====================================
  function initGeneratePage() {
    const classId = document.getElementById("classId").value;
    const generateForm = document.getElementById("generateForm");
    const startBtn = document.getElementById("startBtn");
    const progressSection = document.getElementById("progressSection");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");
    const progressCount = document.getElementById("progressCount");
    const errorAlert = document.getElementById("errorAlert");
    const resultsSection = document.getElementById("resultsSection");
    const resultsBody = document.getElementById("resultsBody");
    const exportBtn = document.getElementById("exportBtn");

    let taskId = null;
    let pollTimer = null;

    // Generate form submit
    generateForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      startBtn.disabled = true;
      startBtn.textContent = "生成中...";

      progressSection.classList.remove("hidden");
      errorAlert.classList.add("hidden");
      resultsSection.classList.add("hidden");

      const style = document.getElementById("style").value;
      const customPrompt = document.getElementById("custom_prompt").value.trim();
      const wordCount = document.getElementById("wordCount").value;

      try {
        const resp = await fetch("/api/v1/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            class_id: parseInt(classId),
            style: style,
            custom_prompt: customPrompt || null,
            word_count: wordCount,
          }),
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "启动生成失败");
        }

        const data = await resp.json();
        taskId = data.task_id;
        progressCount.textContent = "0 / " + data.total;
        startPolling();
      } catch (err) {
        showError(err.message);
        startBtn.disabled = false;
        startBtn.textContent = "\u{1F680} 重新生成评语";
      }
    });

    function startPolling() {
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(pollStatus, 1000);
    }

    async function pollStatus() {
      if (!taskId) return;

      try {
        const resp = await fetch("/api/v1/generate/" + taskId);
        if (!resp.ok) throw new Error("查询状态失败");

        const data = await resp.json();
        updateProgress(data);

        if (data.status === "completed") {
          clearInterval(pollTimer);
          pollTimer = null;
          showResults(data.results);
          startBtn.disabled = false;
          startBtn.textContent = "\u{1F680} 重新生成评语";
        } else if (data.status === "failed") {
          clearInterval(pollTimer);
          pollTimer = null;
          showError(data.error || "生成失败");
          startBtn.disabled = false;
          startBtn.textContent = "\u{1F680} 重新生成评语";
        }
      } catch (err) {
        // Network error, will retry
      }
    }

    function updateProgress(data) {
      const pct = data.total > 0 ? Math.round((data.completed / data.total) * 100) : 0;
      progressFill.style.width = pct + "%";
      progressText.textContent =
        data.status === "processing"
          ? "\u{1F9EE} 正在生成评语..."
          : data.status === "completed"
            ? "✅ 生成完成！"
            : "❌ 生成失败";
      progressCount.textContent = data.completed + " / " + data.total;
    }

    function showResults(results) {
      resultsBody.innerHTML = "";
      progressText.textContent = "✅ 生成完成！";

      results.forEach((r, i) => {
        const hasSensitive = r.sensitive_hit > 0;
        const sensitiveHtml = hasSensitive
          ? '<span class="sensitive-badge">⚠️ 含敏感词</span>'
          : '<span class="safe-badge">✅ 安全</span>';

        const contentPreview = r.content.length > 120
          ? escHtml(r.content.slice(0, 120)) + "..."
          : escHtml(r.content);

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${i + 1}</td>
          <td>${escHtml(r.name)}</td>
          <td>${r.score !== null && r.score !== undefined ? r.score : "-"}</td>
          <td>${escHtml(r.performance || "-")}</td>
          <td>${escHtml(r.homework || "-")}</td>
          <td class="eval-cell">${contentPreview}</td>
          <td>${sensitiveHtml}</td>
          <td>
            <button class="btn-small btn-edit" data-student-id="${r.student_id}" data-content="${escHtml(r.content)}">
              编辑
            </button>
          </td>
        `;
        resultsBody.appendChild(tr);
      });

      resultsSection.classList.remove("hidden");
      resultsSection.scrollIntoView({ behavior: "smooth" });
      bindEditButtons();
    }

    function showError(msg) {
      errorAlert.textContent = "❌ " + msg;
      errorAlert.classList.remove("hidden");
    }

    // ============ Edit Modal ============
    let currentEditStudentId = null;

    function bindEditButtons() {
      document.querySelectorAll(".btn-edit").forEach((btn) => {
        btn.addEventListener("click", function () {
          openEditModal(
            parseInt(this.dataset.studentId),
            this.dataset.content
          );
        });
      });
    }

    function openEditModal(studentId, content) {
      currentEditStudentId = studentId;
      document.getElementById("modalContent").value = content;

      // Check sensitive words
      fetch("/api/v1/classes/" + classId + "/evaluations")
        .then((r) => r.json())
        .then((data) => {
          const student = data.students.find((s) => s.student_id === studentId);
          if (student && student.sensitive_hit > 0) {
            const alert = document.getElementById("modalSensitive");
            alert.innerHTML =
              '⚠️ 该评语含 ' +
              student.sensitive_words.length +
              ' 个敏感词: ' +
              student.sensitive_words.join(", ");
            alert.classList.remove("hidden");
          } else {
            document.getElementById("modalSensitive").classList.add("hidden");
          }
        })
        .catch(() => {});

      document.getElementById("modalStudent").textContent =
        "学生ID: " + studentId;
      document.getElementById("editModal").classList.remove("hidden");
    }

    document.getElementById("modalClose").addEventListener("click", closeModal);
    document.getElementById("modalCancel").addEventListener("click", closeModal);

    function closeModal() {
      document.getElementById("editModal").classList.add("hidden");
      currentEditStudentId = null;
    }

    document.getElementById("modalSave").addEventListener("click", async function () {
      if (!currentEditStudentId) return;

      // Find eval_id from results table
      const content = document.getElementById("modalContent").value.trim();
      if (!content) {
        alert("评语不能为空");
        return;
      }

      try {
        const resp = await fetch("/api/v1/classes/" + classId + "/evaluations");
        const data = await resp.json();
        const student = data.students.find(
          (s) => s.student_id === currentEditStudentId
        );

        if (!student || !student.eval_id) {
          alert("评语记录不存在");
          return;
        }

        const updateResp = await fetch(
          "/api/v1/evaluations/" + student.eval_id,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: content }),
          }
        );

        if (!updateResp.ok) throw new Error("保存失败");

        // Refresh the results table
        const genResp = await fetch("/api/v1/generate/" + taskId);
        const genData = await genResp.json();
        showResults(genData.results);

        closeModal();
      } catch (err) {
        alert("保存失败: " + err.message);
      }
    });

    // ============ Export ============
    exportBtn.addEventListener("click", async function () {
      try {
        exportBtn.disabled = true;
        exportBtn.textContent = "导出中...";

        const resp = await fetch("/api/v1/export-excel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ class_id: parseInt(classId) }),
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "导出失败");
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "评语_" + classId + ".xlsx";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        alert("导出失败: " + err.message);
      } finally {
        exportBtn.disabled = false;
        exportBtn.textContent = "\u{1F4E5} 导出 Excel";
      }
    });
  }

  // =====================================
  // Utilities
  // =====================================
  function escHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
});
