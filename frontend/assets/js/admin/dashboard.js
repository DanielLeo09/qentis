// ─────────────────────────────────────────────
// Qentis — Admin Dashboard
// ─────────────────────────────────────────────

async function loadDashboard() {
    try {
        // Load pending institutions
        const pendingRes = await fetch(`${API_BASE.INSTITUTION}/pending/`, {
            headers: headers.auth()
        });
        const pending = await pendingRes.json();
        const pendingList = Array.isArray(pending) ? pending : [];
        document.getElementById('stat-pending').textContent = pendingList.length;

        if (pendingList.length === 0) {
            document.getElementById('pending-list').innerHTML =
                '<p class="q-empty">No pending applications.</p>';
        } else {
            document.getElementById('pending-list').innerHTML = `
                <table class="q-table">
                    <thead>
                        <tr>
                            <th>Institution</th>
                            <th>Type</th>
                            <th>Country</th>
                            <th>Applied</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${pendingList.slice(0, 5).map(inst => `
                            <tr>
                                <td>${inst.name}</td>
                                <td>${inst.institution_type}</td>
                                <td>${inst.country}</td>
                                <td>${formatDate(inst.created_at)}</td>
                                <td>
                                    <a href="pending-issuers.html"
                                       class="btn-q-primary"
                                       style="padding:4px 12px;font-size:12px">
                                        Review
                                    </a>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }

        // Load all institutions
        const allRes = await fetch(`${API_BASE.INSTITUTION}/all/`, {
            headers: headers.auth()
        });
        const allData = await allRes.json();
        const allInstitutions = Array.isArray(allData) ? allData : [];
        document.getElementById('stat-institutions').textContent = allInstitutions.length;

        // Load fraud flags
        const flagsRes = await fetch(`${API_BASE.VERIFICATION}/flags/`, {
            headers: headers.auth()
        });
        const flagsData = await flagsRes.json();
        const flags = Array.isArray(flagsData) ? flagsData : [];
        const openFlags = flags.filter(f => f.status === 'OPEN');
        document.getElementById('stat-flags').textContent = openFlags.length;

        if (openFlags.length === 0) {
            document.getElementById('flags-list').innerHTML =
                '<p class="q-empty">No open fraud flags.</p>';
        } else {
            document.getElementById('flags-list').innerHTML = `
                <table class="q-table">
                    <thead>
                        <tr>
                            <th>Item ID</th>
                            <th>Verifications</th>
                            <th>Flagged At</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${openFlags.slice(0, 5).map(flag => `
                            <tr>
                                <td style="font-family:monospace;font-size:12px">
                                    ${flag.item_id}
                                </td>
                                <td>${flag.verification_count}</td>
                                <td>${formatDateTime(flag.flagged_at)}</td>
                                <td>
                                    <span class="q-badge q-badge--warning">OPEN</span>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }

        // Placeholder stats
        document.getElementById('stat-items').textContent = '—';
        document.getElementById('stat-verifications').textContent = '—';

    } catch (error) {
        console.error('Dashboard load error:', error);
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);