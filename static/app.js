let entity = "customers";        // the table shown on the right: "customers", "products" or "invoices"
let conversationId = null;       // one chat for everything; the server routes each message to the right bot

function addMessage(who, text) {
  /* Show one line in the chat: who is "You", "Bot" or "System". Returns the new element. */
  const line = document.createElement("div");
  line.className = "message " + who.toLowerCase();
  line.textContent = who + ": " + text;
  const box = document.getElementById("messages");
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
  return line;
}

async function sendMessage(text) {
  /* Send one chat message to the single chat (the server picks the bot) and show its answer or proposal. */
  addMessage("You", text);
  const waiting = addMessage("Bot", "…");
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: text, conversation_id: conversationId}),
    });
    const data = await response.json();
    waiting.remove();
    if (!response.ok) {
      addMessage("System", "Error: " + JSON.stringify(data.detail || data));
      return;
    }
    conversationId = data.conversation_id;
    const who = data.entity ? `Bot (${data.entity})` : "Bot";   // shows which bot answered
    if (data.proposal) {
      showProposal(data.proposal, who);
    } else {
      addMessage(who, data.reply).className = "message bot";
      if ((data.ui || []).includes("customer")) showRecordPicker("customer");
      if ((data.ui || []).includes("product")) showRecordPicker("product");
      if ((data.ui || []).includes("turnover")) showTurnoverPicker("customer");
      if ((data.ui || []).includes("product_turnover")) showTurnoverPicker("product");
      if ((data.ui || []).includes("monthly_turnover")) showMonthlyTurnoverPicker();
      if ((data.ui || []).includes("dates")) showDatePicker();
      if ((data.ui || []).includes("lines")) showLinePicker();
    }
  } catch (error) {
    waiting.remove();
    addMessage("System", "The server could not be reached: " + error.message);
  }
}

const COLUMNS = {
  customers: ["id", "name", "address"],
  products: ["id", "name", "sell_price", "buy_price"],
  invoices: ["id", "customer_id", "date", "due_date", "status"],
};

async function loadList() {
  /* Show all records of the active tab as a table. */
  const table = document.getElementById("list-table");
  const response = await fetch(`/${entity}`);
  const records = await response.json();
  const columns = COLUMNS[entity];
  table.innerHTML = "";
  const header = table.insertRow();
  columns.forEach(c => { const th = document.createElement("th"); th.textContent = c; header.appendChild(th); });
  records.forEach(record => {
    const row = table.insertRow();
    columns.forEach(c => { row.insertCell().textContent = record[c] ?? ""; });
  });
}

function switchTab(newEntity) {
  /* Switch the table on the right to another entity ("customers", "products" or "invoices"); the chat stays. */
  entity = newEntity;
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("active", b.dataset.entity === entity));
  document.getElementById("list-title").textContent = entity[0].toUpperCase() + entity.slice(1);
  loadList();
}

document.querySelectorAll("#tabs button").forEach(button => {
  button.onclick = () => switchTab(button.dataset.entity);
});

document.getElementById("chat-form").onsubmit = event => {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (text) {
    sendMessage(text);
    input.value = "";
  }
};

loadList();

function toDisplayDate(isoDate) {
  /* "2026-10-09" (date input) -> "09/10/2026" (our DD/MM/YYYY format). */
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

function showDatePicker() {
  /* Calendar fields for a new invoice: the invoice date cannot be in the past, the due date not before it.
     "Use these dates" sends them to the invoice bot as a normal chat message. */
  const now = new Date();  // local date, YYYY-MM-DD
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const box = document.createElement("div");
  box.className = "message system date-picker";
  box.innerHTML = `<label>Invoice date <input type="date" class="invoice-date" min="${today}" value="${today}"></label>
                   <label>Due date <input type="date" class="due-date" min="${today}"></label>
                   <button disabled>Use these dates</button>`;
  const invoiceDate = box.querySelector(".invoice-date");
  const dueDate = box.querySelector(".due-date");
  const use = box.querySelector("button");
  const update = () => {
    if (invoiceDate.value < today) invoiceDate.value = today;
    dueDate.min = invoiceDate.value;
    if (dueDate.value && dueDate.value < invoiceDate.value) dueDate.value = "";
    use.disabled = !(invoiceDate.value && dueDate.value);
  };
  invoiceDate.onchange = update;
  dueDate.onchange = update;
  use.onclick = () => {
    box.remove();
    sendMessage(`invoice date ${toDisplayDate(invoiceDate.value)}, due date ${toDisplayDate(dueDate.value)}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
  update();
}

async function showRecordPicker(kind) {
  /* Choose an existing customer or product ("customer" / "product"): a search field with all records (sorted A-Z;
     typing narrows the list, so it also works with many records). Only an existing record can be used; it is sent
     to the bot as "customer: Name" or "product: Name". */
  const records = (await (await fetch(`/${kind}s`)).json()).sort((a, b) => a.name.localeCompare(b.name));
  const hint = r => kind === "customer" ? r.address : `sell price ${Number(r.sell_price).toFixed(2)}`;
  const listId = `${kind}-list-` + Date.now();
  const box = document.createElement("div");
  box.className = "message system record-picker";
  box.innerHTML = `<label>${kind[0].toUpperCase() + kind.slice(1)} <input class="record" list="${listId}" placeholder="type to search"></label>
                   <datalist id="${listId}"></datalist>
                   <button disabled>Use this ${kind}</button>`;
  const list = box.querySelector("datalist");
  records.forEach(r => list.appendChild(new Option(hint(r), r.name)));
  const input = box.querySelector(".record");
  const use = box.querySelector("button");
  input.oninput = () => { use.disabled = !records.some(r => r.name === input.value); };
  use.onclick = () => {
    box.remove();
    sendMessage(`${kind}: ${input.value}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
}

async function showTurnoverPicker(kind) {
  /* Turnover question per customer or per product (kind "customer" / "product"): start and end date (the end not
     before the start) and optionally one customer or product (empty = all). "Show turnover" sends it to the bot as
     one message it accepts as given. */
  const records = (await (await fetch(`/${kind}s`)).json()).sort((a, b) => a.name.localeCompare(b.name));
  const hint = r => kind === "customer" ? r.address : `sell price ${Number(r.sell_price).toFixed(2)}`;
  const label = kind[0].toUpperCase() + kind.slice(1);
  const listId = `turnover-${kind}s-` + Date.now();
  const box = document.createElement("div");
  box.className = "message system date-picker";
  box.innerHTML = `<label>From <input type="date" class="start"></label>
                   <label>To <input type="date" class="end"></label>
                   <label>${label} <input class="record" list="${listId}" placeholder="all ${kind}s"></label>
                   <datalist id="${listId}"></datalist>
                   <button disabled>Show turnover</button>`;
  records.forEach(r => box.querySelector("datalist").appendChild(new Option(hint(r), r.name)));
  // Turnover per customer can also be limited to one product (sent with its id, so the bot never looks it up).
  const products = kind === "customer"
    ? (await (await fetch("/products")).json()).sort((a, b) => a.name.localeCompare(b.name)) : [];
  let product = null;
  if (kind === "customer") {
    const productList = `${listId}-products`;
    const label = document.createElement("label");
    label.innerHTML = `Product <input class="product" list="${productList}" placeholder="all products"><datalist id="${productList}"></datalist>`;
    products.forEach(p => label.querySelector("datalist").appendChild(new Option(`sell price ${Number(p.sell_price).toFixed(2)}`, p.name)));
    box.insertBefore(label, box.querySelector("button"));
    product = label.querySelector(".product");
  }
  const start = box.querySelector(".start");
  const end = box.querySelector(".end");
  const record = box.querySelector(".record");
  const show = box.querySelector("button");
  const update = () => {
    end.min = start.value;
    if (end.value && start.value && end.value < start.value) end.value = "";
    const recordOk = record.value === "" || records.some(r => r.name === record.value);
    const productOk = !product || product.value === "" || products.some(p => p.name === product.value);
    show.disabled = !(start.value && end.value && recordOk && productOk);
  };
  start.onchange = update;
  end.onchange = update;
  record.oninput = update;
  if (product) product.oninput = update;
  show.onclick = () => {
    box.remove();
    const picked = records.find(r => r.name === record.value);  // sent with its id, so the bot never looks it up
    const which = picked ? `${kind}: ${picked.name}${kind === "customer" ? ` (${picked.id})` : ""}` : `all ${kind}s`;
    const prefix = kind === "product" ? "product turnover" : "turnover";
    const chosen = product && products.find(p => p.name === product.value);
    const productPart = kind === "customer" ? `, ${chosen ? `product: ${chosen.name} (${chosen.id})` : "all products"}` : "";
    sendMessage(`${prefix} from ${toDisplayDate(start.value)} to ${toDisplayDate(end.value)}, ${which}${productPart}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
}

async function showMonthlyTurnoverPicker() {
  /* Turnover month by month: a year and optionally a customer and/or a product (empty = all). The chosen records
     are sent with their ids, so the bot never has to look an id up: "monthly turnover for 2026, customer: Felix
     Hartmann (CUS-001), all products". */
  const [customers, products] = await Promise.all(["customers", "products"].map(async kind =>
    (await (await fetch(`/${kind}`)).json()).sort((a, b) => a.name.localeCompare(b.name))));
  const stamp = Date.now();
  const box = document.createElement("div");
  box.className = "message system date-picker";
  box.innerHTML = `<label>Year <input type="number" class="year" min="2000" max="2100" step="1" value="${new Date().getFullYear()}"></label>
                   <label>Customer <input class="customer" list="mc-${stamp}" placeholder="all customers"></label>
                   <datalist id="mc-${stamp}"></datalist>
                   <label>Product <input class="product" list="mp-${stamp}" placeholder="all products"></label>
                   <datalist id="mp-${stamp}"></datalist>
                   <button>Show turnover</button>`;
  customers.forEach(c => box.querySelector(`#mc-${stamp}`).appendChild(new Option(c.address, c.name)));
  products.forEach(p => box.querySelector(`#mp-${stamp}`).appendChild(new Option(`sell price ${Number(p.sell_price).toFixed(2)}`, p.name)));
  const year = box.querySelector(".year");
  const customer = box.querySelector(".customer");
  const product = box.querySelector(".product");
  const show = box.querySelector("button");
  const find = (records, name) => records.find(r => r.name === name);
  const update = () => {
    const yearOk = /^\d{4}$/.test(year.value);
    show.disabled = !(yearOk && (customer.value === "" || find(customers, customer.value))
                      && (product.value === "" || find(products, product.value)));
  };
  [year, customer, product].forEach(input => input.oninput = update);
  show.onclick = () => {
    box.remove();
    const c = find(customers, customer.value);
    const p = find(products, product.value);
    sendMessage(`monthly turnover for ${year.value}, ${c ? `customer: ${c.name} (${c.id})` : "all customers"}, `
                + `${p ? `product: ${p.name} (${p.id})` : "all products"}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
  update();
}

async function showLinePicker() {
  /* Invoice lines: choose products from the available ones (sorted A-Z) with a quantity, collect them, then
     "Use these lines" sends them to the invoice bot as a normal chat message, e.g. "products: 2 Desk Lamp". */
  const products = (await (await fetch("/products")).json()).sort((a, b) => a.name.localeCompare(b.name));
  const box = document.createElement("div");
  box.className = "message system line-picker";
  box.innerHTML = `<div><select class="product"></select>
                   <input type="number" class="quantity" min="1" step="1" value="1">
                   <button class="add">Add line</button></div>
                   <ul class="chosen"></ul>
                   <button class="use" disabled>Use these lines</button>`;
  products.forEach(p => box.querySelector(".product").add(new Option(`${p.name} (${Number(p.sell_price).toFixed(2)})`, p.name)));
  const lines = [];
  const chosen = box.querySelector(".chosen");
  const use = box.querySelector(".use");
  box.querySelector(".add").onclick = () => {
    const quantity = parseInt(box.querySelector(".quantity").value, 10);
    if (!(quantity >= 1)) return;
    lines.push(`${quantity} ${box.querySelector(".product").value}`);
    const item = document.createElement("li");
    item.textContent = lines[lines.length - 1];
    chosen.appendChild(item);
    use.disabled = false;
  };
  use.onclick = () => {
    box.remove();
    sendMessage(`products: ${lines.join(", ")}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
}

function showProposal(proposal, who = "Bot") {
  /* Show the proposal's summary with Yes / No buttons. Yes saves it, No cancels it. */
  const line = addMessage(who, proposal.summary);
  line.className = "message bot";
  const yes = document.createElement("button");
  const no = document.createElement("button");
  yes.textContent = "Yes";
  no.textContent = "No";
  yes.onclick = () => { line.querySelectorAll("button").forEach(b => b.remove()); confirmProposal(proposal); };
  no.onclick = () => { line.querySelectorAll("button").forEach(b => b.remove()); addMessage("System", "Cancelled. Nothing was saved."); };
  line.append(" ", yes, " ", no);
}

async function confirmProposal(proposal) {
  /* The user said yes: send the proposal to the CRUD endpoint, show the result and refresh the list. */
  try {
    const response = await fetch(proposal.path, {
      method: proposal.method,
      headers: {"Content-Type": "application/json"},
      body: proposal.body ? JSON.stringify(proposal.body) : undefined,
    });
    const data = await response.json();
    if (!response.ok) {
      addMessage("System", "Not saved: " + JSON.stringify(data.detail || data));
      return;
    }
    const done = {POST: "Saved as", PUT: "Changed", DELETE: "Deleted"}[proposal.method];
    addMessage("System", `${done} ${data.id}.`);
    loadList();
  } catch (error) {
    addMessage("System", "The server could not be reached: " + error.message);
  }
}
