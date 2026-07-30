const STORAGE_KEY = "savarjisho3.contacts";

const form = document.getElementById("contact-form");
const nameInput = document.getElementById("name");
const phoneInput = document.getElementById("phone");
const listEl = document.getElementById("contacts");
const countEl = document.getElementById("count");
const emptyEl = document.getElementById("empty");
const itemTemplate = document.getElementById("contact-item");

function loadContacts() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveContacts(contacts) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(contacts));
}

function normalizePhone(phone) {
  return phone.trim().replace(/\s+/g, " ");
}

function telHref(phone) {
  const digits = phone.replace(/[^\d+]/g, "");
  return `tel:${digits}`;
}

function escapeVcard(value) {
  return String(value)
    .replace(/\\/g, "\\\\")
    .replace(/\n/g, "\\n")
    .replace(/,/g, "\\,")
    .replace(/;/g, "\\;");
}

function buildVcard({ name, phone }) {
  const safeName = escapeVcard(name);
  const safePhone = escapeVcard(normalizePhone(phone));
  return [
    "BEGIN:VCARD",
    "VERSION:3.0",
    `FN:${safeName}`,
    `N:;${safeName};;;`,
    `TEL;TYPE=CELL:${safePhone}`,
    "END:VCARD",
  ].join("\r\n");
}

function downloadVcard(contact) {
  const blob = new Blob([buildVcard(contact)], {
    type: "text/vcard;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const fileSafe = contact.name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9ა-ჰ-_]+/gi, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  anchor.href = url;
  anchor.download = `${fileSafe || "contact"}.vcf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function render(contacts) {
  listEl.replaceChildren();
  countEl.textContent = String(contacts.length);
  emptyEl.hidden = contacts.length > 0;

  for (const contact of contacts) {
    const node = itemTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".contact-name").textContent = contact.name;
    node.querySelector(".contact-phone").textContent = contact.phone;

    const call = node.querySelector(".call");
    call.href = telHref(contact.phone);

    node.querySelector(".save").addEventListener("click", () => {
      downloadVcard(contact);
    });

    node.querySelector(".delete").addEventListener("click", () => {
      const next = loadContacts().filter((item) => item.id !== contact.id);
      saveContacts(next);
      render(next);
    });

    listEl.appendChild(node);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const name = nameInput.value.trim();
  const phone = normalizePhone(phoneInput.value);

  if (!name || !phone) return;

  const contacts = loadContacts();
  contacts.unshift({
    id: crypto.randomUUID(),
    name,
    phone,
    createdAt: Date.now(),
  });
  saveContacts(contacts);
  render(contacts);

  form.reset();
  nameInput.focus();
});

render(loadContacts());
