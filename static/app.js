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
      if ((data.ui || []).includes("invoice")) showInvoicePicker();
      if ((data.ui || []).includes("status")) showStatusPicker();
      if ((data.ui || []).includes("edit_product")) showProductEditForm();
      if ((data.ui || []).includes("new_customer")) {
        const known = (data.reply.match(/address of (.+?)\?/) || [])[1] || "";  // "What is the address of Bob?" -> "Bob"
        showCustomerForm(known);
      }
      if ((data.ui || []).includes("new_product")) {
        const known = (data.reply.match(/price of (.+?)\?/) || [])[1] || "";  // "What is the sell price of X?" -> "X"
        showProductForm(known);
      }
    }
  } catch (error) {
    waiting.remove();
    addMessage("System", "The server could not be reached: " + error.message);
  }
}

const COLUMNS = {
  customers: ["id", "name", "address"],
  products: ["id", "name", "sell_price"],
  invoices: ["id", "customer_id", "date", "due_date", "status", "total"],
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

async function askHelp(text) {
  /* "Help": answer a question about using this software from the user guide (server: guide.answer). Never saves. */
  addMessage("You", text);
  const waiting = addMessage("Help", "…");
  try {
    const response = await fetch("/help", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: text, conversation_id: null}),
    });
    const data = await response.json();
    waiting.remove();
    addMessage("Help", response.ok ? data.reply : "Error: " + JSON.stringify(data.detail || data));
  } catch (error) {
    waiting.remove();
    addMessage("System", "The server could not be reached: " + error.message);
  }
}

document.getElementById("help-button").onclick = () => {
  const input = document.getElementById("chat-input");
  const text = input.value.trim() || "How do I use the chat?";  // empty field: a first overview
  askHelp(text);
  input.value = "";
};

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

function showStatusPicker() {
  /* Paid or unpaid for a new invoice: two buttons; the choice is sent to the invoice bot as "paid" or "unpaid". */
  const box = document.createElement("div");
  box.className = "message system date-picker";
  box.innerHTML = `<button data-status="paid">Paid</button> <button data-status="unpaid">Unpaid</button>`;
  box.querySelectorAll("button").forEach(button => button.onclick = () => {
    box.remove();
    sendMessage(button.dataset.status);
  });
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
}

function showCustomerForm(name = "") {
  /* A new customer: name and address, both required. The name is filled in if the bot already knows it.
     "Create customer" sends it to the customer bot in the form it accepts directly:
     "add customer Lisa Kraus, Kirchweg 2, 48143 Münster". */
  const box = document.createElement("div");
  box.className = "message system date-picker";
  box.innerHTML = `<label>Name <input class="name" placeholder="first and last name"></label>
                   <label>Address <input class="address" placeholder="street, postcode city"></label>
                   <button disabled>Create customer</button>`;
  const nameInput = box.querySelector(".name");
  const address = box.querySelector(".address");
  const create = box.querySelector("button");
  nameInput.value = name;
  const update = () => { create.disabled = !(nameInput.value.trim() && address.value.trim()); };
  nameInput.oninput = update;
  address.oninput = update;
  create.onclick = () => {
    box.remove();
    sendMessage(`add customer ${nameInput.value.trim()}, ${address.value.trim()}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
}

function showProductForm(name = "") {
  /* A new product: name and sell price (a number >= 0). The name is filled in if the bot already knows it.
     "Create product" sends it in the form the product bot accepts directly: "new product Monitor 32, sell price 249.00". */
  const box = document.createElement("div");
  box.className = "message system date-picker";
  box.innerHTML = `<label>Name <input class="name" placeholder="product name"></label>
                   <label>Sell price <input type="number" class="sell" min="0" step="0.01"></label>
                   <button disabled>Create product</button>`;
  const nameInput = box.querySelector(".name");
  const sell = box.querySelector(".sell");
  const create = box.querySelector("button");
  nameInput.value = name;
  const price = input => input.value !== "" && Number(input.value) >= 0;
  const update = () => {
    create.disabled = !(nameInput.value.trim() && price(sell));
  };
  [nameInput, sell].forEach(input => input.oninput = update);
  create.onclick = () => {
    box.remove();
    sendMessage(`new product ${nameInput.value.trim()}, sell price ${Number(sell.value).toFixed(2)}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
}

async function showProductEditForm() {
  /* Change a product's price: choose the product and the new sell price (>= 0) in one form, so the
     bot gets everything in one message it accepts directly: "product: Desk Lamp, new sell price 30.00". */
  const products = (await (await fetch("/products")).json()).sort((a, b) => a.name.localeCompare(b.name));
  const listId = "edit-product-list-" + Date.now();
  const box = document.createElement("div");
  box.className = "message system date-picker";
  box.innerHTML = `<label>Product <input class="record" list="${listId}" placeholder="type to search"></label>
                   <datalist id="${listId}"></datalist>
                   <label>New sell price <input type="number" class="price" min="0" step="0.01"></label>
                   <button disabled>Change price</button>`;
  products.forEach(p => box.querySelector("datalist").appendChild(new Option(
    `sell ${Number(p.sell_price).toFixed(2)}`, p.name)));
  const record = box.querySelector(".record");
  const price = box.querySelector(".price");
  const change = box.querySelector("button");
  const update = () => {
    change.disabled = !(products.some(p => p.name === record.value) && price.value !== "" && Number(price.value) >= 0);
  };
  [record, price].forEach(input => input.oninput = update);
  change.onclick = () => {
    box.remove();
    sendMessage(`product: ${record.value}, new sell price ${Number(price.value).toFixed(2)}`);
  };
  const messages = document.getElementById("messages");
  messages.appendChild(box);
  messages.scrollTop = messages.scrollHeight;
}

async function showInvoicePicker() {
  /* Choose an existing invoice: a search field with all invoices (newest first), each shown with customer, status
     and total. Only an existing number can be used; it is sent to the invoice bot as the bare number "INV-001". */
  const [invoices, customers] = await Promise.all(["invoices", "customers"].map(async kind =>
    (await fetch(`/${kind}`)).json()));
  const name = id => (customers.find(c => c.id === id) || {}).name || id;
  const listId = "invoice-list-" + Date.now();
  const box = document.createElement("div");
  box.className = "message system record-picker";
  box.innerHTML = `<label>Invoice <input class="record" list="${listId}" placeholder="type to search"></label>
                   <datalist id="${listId}"></datalist>
                   <button disabled>Use this invoice</button>`;
  invoices.slice().reverse().forEach(i => box.querySelector("datalist").appendChild(
    new Option(`${name(i.customer_id)} | ${i.status} | ${Number(i.total).toFixed(2)}`, i.id)));
  const input = box.querySelector(".record");
  const use = box.querySelector("button");
  input.oninput = () => { use.disabled = !invoices.some(i => i.id === input.value); };
  use.onclick = () => {
    box.remove();
    sendMessage(input.value);
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
  // each entry is "name (id)", so two customers with the same name stay different
  const entry = r => `${r.name} (${r.id})`;
  records.forEach(r => box.querySelector("datalist").appendChild(new Option(hint(r), entry(r))));
  // Turnover per customer can also be limited to one product, turnover per product to one customer
  // (sent with its id, so the bot never looks it up).
  const other = kind === "customer" ? "product" : "customer";
  const extras = (await (await fetch(`/${other}s`)).json()).sort((a, b) => a.name.localeCompare(b.name));
  const extraHint = r => other === "customer" ? r.address : `sell price ${Number(r.sell_price).toFixed(2)}`;
  const extraList = `${listId}-${other}s`;
  const extraLabel = document.createElement("label");
  extraLabel.innerHTML = `${other[0].toUpperCase() + other.slice(1)} <input class="extra" list="${extraList}" placeholder="all ${other}s"><datalist id="${extraList}"></datalist>`;
  extras.forEach(r => extraLabel.querySelector("datalist").appendChild(new Option(extraHint(r), entry(r))));
  box.insertBefore(extraLabel, box.querySelector("button"));
  const extra = extraLabel.querySelector(".extra");
  const start = box.querySelector(".start");
  const end = box.querySelector(".end");
  const record = box.querySelector(".record");
  const show = box.querySelector("button");
  const update = () => {
    end.min = start.value;
    if (end.value && start.value && end.value < start.value) end.value = "";
    const recordOk = record.value === "" || records.some(r => entry(r) === record.value);
    const extraOk = extra.value === "" || extras.some(r => entry(r) === extra.value);
    show.disabled = !(start.value && end.value && recordOk && extraOk);
  };
  start.onchange = update;
  end.onchange = update;
  record.oninput = update;
  extra.oninput = update;
  show.onclick = () => {
    box.remove();
    const picked = records.find(r => entry(r) === record.value);  // sent with its id, Python uses the id
    const which = picked ? `${kind}: ${entry(picked)}` : `all ${kind}s`;
    const prefix = `turnover per ${kind}`;  // names the kind, so the bot picks the right tool
    const chosen = extras.find(r => entry(r) === extra.value);
    const extraPart = chosen ? `, ${other}: ${entry(chosen)}` : "";  // nothing chosen: no filter
    sendMessage(`${prefix} from ${toDisplayDate(start.value)} to ${toDisplayDate(end.value)}, ${which}${extraPart}`);
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
  const entry = r => `${r.name} (${r.id})`;  // "name (id)", so two records with the same name stay different
  customers.forEach(c => box.querySelector(`#mc-${stamp}`).appendChild(new Option(c.address, entry(c))));
  products.forEach(p => box.querySelector(`#mp-${stamp}`).appendChild(new Option(`sell price ${Number(p.sell_price).toFixed(2)}`, entry(p))));
  const year = box.querySelector(".year");
  const customer = box.querySelector(".customer");
  const product = box.querySelector(".product");
  const show = box.querySelector("button");
  const find = (records, value) => records.find(r => entry(r) === value);
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
