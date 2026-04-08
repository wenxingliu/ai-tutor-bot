const uploadForm = document.querySelector("#upload-form");
const uploadInput = document.querySelector("#pdf-files");
const uploadStatus = document.querySelector("#upload-status");
const chatForm = document.querySelector("#chat-form");
const chatStatus = document.querySelector("#chat-status");
const questionInput = document.querySelector("#question");
const messages = document.querySelector("#messages");
const template = document.querySelector("#message-template");

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!uploadInput.files.length) {
    uploadStatus.textContent = "Select at least one PDF.";
    return;
  }

  uploadStatus.textContent = "Uploading and indexing...";

  const formData = new FormData();
  for (const file of uploadInput.files) {
    formData.append("files", file);
  }

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Upload failed.");
    }
    uploadStatus.textContent = `${payload.message} ${payload.chunks_indexed} chunks indexed.`;
  } catch (error) {
    uploadStatus.textContent = error.message;
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  if (!question) {
    chatStatus.textContent = "Enter a question first.";
    return;
  }

  appendMessage("Student", question);
  questionInput.value = "";
  chatStatus.textContent = "Thinking...";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Request failed.");
    }

    appendMessage("Tutor", payload.answer, payload.sources);
    chatStatus.textContent = "";
  } catch (error) {
    chatStatus.textContent = error.message;
  }
});

function appendMessage(author, body, sources = []) {
  const node = template.content.firstElementChild.cloneNode(true);
  node.querySelector(".message-header").textContent = author;
  node.querySelector(".message-body").textContent = body;

  const details = node.querySelector(".sources");
  if (!sources.length) {
    details.remove();
  } else {
    const sourceList = node.querySelector(".source-list");
    for (const source of sources) {
      const card = document.createElement("section");
      card.className = "source-card";

      const meta = document.createElement("p");
      meta.className = "source-meta";
      meta.textContent = `${source.filename}, page ${source.page_number}, score ${source.score}`;

      const text = document.createElement("p");
      text.className = "source-text";
      text.textContent = source.content;

      card.append(meta, text);
      sourceList.append(card);
    }
  }

  messages.append(node);
  node.scrollIntoView({ behavior: "smooth", block: "end" });
}
