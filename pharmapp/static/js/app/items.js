(() => {
  const API = document.body.dataset.api;
  const FIELDS = [['name','Name','text'],['brand','Brand','text'],['dosage_form','Dosage form','text'],['unit','Unit','text'],
    ['cost','Cost','number'],['markup','Markup %','number'],['price','Price','number'],['stock','Stock','number'],
    ['exp_date','Expiry','date'],['barcode','Barcode','text']];
  const $ = s => document.querySelector(s);
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let editId = null, items = [];

  async function api(url, method = 'GET', body) {
    const r = await fetch(url, {
      method, credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()},
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw Object.assign(new Error(data.error || 'Request failed'), {status: r.status, errors: data.errors});
    return data;
  }

  const show = m => { $('#msg').textContent = m || ''; };

  function render() {
    $('#rows').innerHTML = items.map(i => `<tr>
      <td>${esc(i.name)}</td><td>${esc(i.brand)}</td><td>${esc(i.dosage_form)}</td><td>${esc(i.unit)}</td>
      <td>${esc(i.cost)}</td><td>${esc(i.price)}</td><td>${esc(i.stock)}</td><td>${esc(i.exp_date)}</td>
      <td class="text-nowrap"><button class="btn btn-sm btn-outline-primary" data-edit="${i.id}">Edit</button>
      <button class="btn btn-sm btn-outline-danger" data-del="${i.id}">Delete</button></td></tr>`).join('')
      || '<tr><td colspan="9" class="text-muted">No items</td></tr>';
  }

  async function load() {
    try { items = (await api(API + '?q=' + encodeURIComponent($('#q').value))).items; show(); render(); }
    catch (e) { show(e.message); }
  }

  function openForm(item) {
    editId = item ? item.id : null;
    $('#dlg-title').textContent = item ? 'Edit item' : 'Add item';
    $('#fields').innerHTML = FIELDS.map(([n, l, t]) =>
      `<div class="form-group mb-2"><label class="mb-0">${l}</label>
       <input class="form-control" name="${n}" type="${t}" ${t === 'number' ? 'step="any"' : ''} value="${esc(item ? item[n] : '')}">
       <div class="err" data-err="${n}"></div></div>`).join('');
    $('#dlg').showModal();
  }

  $('#f').addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(e.target), body = Object.fromEntries(fd);
    body.manual_price_override = fd.has('manual_price_override');
    document.querySelectorAll('[data-err]').forEach(d => d.textContent = '');
    try {
      await api(editId ? API + editId + '/' : API, editId ? 'PUT' : 'POST', body);
      $('#dlg').close(); load();
    } catch (err) {
      if (err.errors) for (const [k, v] of Object.entries(err.errors)) {
        const d = document.querySelector(`[data-err="${k}"]`); if (d) d.textContent = v.join(' ');
      } else show(err.message);
    }
  });

  $('#add').onclick = () => openForm();
  $('#cancel').onclick = () => $('#dlg').close();
  let t; $('#q').oninput = () => { clearTimeout(t); t = setTimeout(load, 250); };
  $('#rows').addEventListener('click', async e => {
    const ed = e.target.dataset.edit, del = e.target.dataset.del;
    if (ed) openForm(items.find(i => i.id == ed));
    if (del && confirm('Delete this item?')) {
      try { await api(API + del + '/', 'DELETE'); load(); } catch (err) { show(err.message); }
    }
  });
  load();
})();
