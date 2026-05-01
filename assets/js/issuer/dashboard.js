async function loadDashboard() {
  try {
    const res  = await qFetch(`${API.ITEMS}/items/?limit=5`);
    const data = await res.json();

    document.getElementById('stat-total').textContent = data.count ?? data.results?.length ?? 0;

    document.getElementById('recent-items-loading').style.display = 'none';

    if (!data.results || data.results.length === 0) {
      document.getElementById('recent-items-empty').style.display = 'block';
      return;
    }

    document.getElementById('recent-items-table').style.display = 'table';
    document.getElementById('recent-items-body').innerHTML = data.results.map(item => `
      <tr>
        <td>
          <div class="item-name">${item.name}</div>
          <div class="item-hash">${formatHash(item.hash)}</div>
        </td>
        <td><span class="q-badge q-badge-active">${item.category}</span></td>
        <td class="td-date">${formatDate(item.created_at)}</td>
        <td><span class="q-badge q-badge-approved">Active</span></td>
        <td><a href="my-items.html?id=${item.id}" class="link-sm">View</a></td>
      </tr>
    `).join('');
  } catch (e) {
    document.getElementById('recent-items-loading').style.display = 'none';
    document.getElementById('recent-items-empty').style.display = 'block';
  }
}

loadDashboard();
