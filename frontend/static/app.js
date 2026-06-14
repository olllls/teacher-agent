document.addEventListener("DOMContentLoaded", function () {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");
    const fileInfo = document.getElementById("fileInfo");
    const fileName = document.getElementById("fileName");
    const removeBtn = document.getElementById("removeFile");
    const submitBtn = document.getElementById("submitBtn");
    const uploadForm = document.getElementById("uploadForm");
    const previewSection = document.getElementById("previewSection");

    let selectedFile = null;

    // Dropzone click
    dropzone.addEventListener("click", () => fileInput.click());

    // Drag & drop
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

    // File input change
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length) {
            handleFile(fileInput.files[0]);
        }
    });

    // Remove file
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

    // Upload form submit
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
                <td>${escapeHtml(s.name)}</td>
                <td>${s.score !== null ? s.score : "-"}</td>
                <td>${escapeHtml(s.performance || "-")}</td>
                <td>${escapeHtml(s.homework || "-")}</td>
            `;
            tbody.appendChild(tr);
        });

        const generateBtn = document.getElementById("generateBtn");
        generateBtn.href = "/generate/" + data.class_id;

        previewSection.classList.remove("hidden");
        previewSection.scrollIntoView({ behavior: "smooth" });

        // Show success message
        const existing = document.querySelector(".alert-success");
        if (existing) existing.remove();
        const alert = document.createElement("div");
        alert.className = "alert alert-success";
        alert.textContent = "✅ 成功解析 " + data.total + " 名学生数据！";
        uploadForm.prepend(alert);
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }
});
