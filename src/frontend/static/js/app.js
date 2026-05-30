// ============================================================
// Hybrid Document-Graph Store - Main Page JavaScript
// ============================================================

const API_BASE = '';

// ============================================================
// State
// ============================================================
let currentResults = [];
let currentQuery = null;

// ============================================================
// DOM Elements
// ============================================================
const queryText = document.getElementById('queryText');
const targetField = document.getElementById('targetField');
const maxDistance = document.getElementById('maxDistance');
const distanceValue = document.getElementById('distanceValue');
const traversalAlgorithm = document.getElementById('traversalAlgorithm');
const textWeight = document.getElementById('textWeight');
const graphWeight = document.getElementById('graphWeight');
const minSeverity = document.getElementById('minSeverity');
const maxResults = document.getElementById('maxResults');
const executeBtn = document.getElementById('executeQuery');
const resultsBody = document.getElementById('resultsBody');
const resultsCount = document.getElementById('resultsCount');
const joinCostPanel = document.getElementById('joinCostPanel');
const joinCostMetrics = document.getElementById('joinCostMetrics');

// Stat elements
const statResults = document.getElementById('statResults');
const statTime = document.getElementById('statTime');
const statPartitions = document.getElementById('statPartitions');
const statCost = document.getElementById('statCost');

// ============================================================
// Event Listeners
// ============================================================
maxDistance.addEventListener('input', () => {
    distanceValue.textContent = maxDistance.value;
});

executeBtn.addEventListener('click', executeHybridQuery);

// Sample query buttons
document.querySelectorAll('.sample-query').forEach(btn => {
    btn.addEventListener('click', () => {
        queryText.value = btn.dataset.query;
        targetField.value = btn.dataset.field;
        executeHybridQuery();
    });
});

document.getElementById('downloadResults').addEventListener('click', downloadResults);

// ============================================================
// API Functions
// ============================================================

async function executeHybridQuery() {
    const q = queryText.value.trim();
    if (!q) {
        alert('Please enter a search query');
        return;
    }

    // Set loading state
    executeBtn.disabled = true;
    executeBtn.innerHTML = '<span class="loading-spinner"></span> Executing...';

    try {
        const response = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query_text: q,
                target_field: targetField.value,
                max_graph_distance: parseInt(maxDistance.value),
                max_results: parseInt(maxResults.value),
                text_weight: parseFloat(textWeight.value),
                graph_weight: parseFloat(graphWeight.value),
                traversal_algorithm: traversalAlgorithm.value,
                min_severity: minSeverity.value ? parseInt(minSeverity.value) : null,
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentResults = data.results;
            currentQuery = data.query;
            renderResults(data);
            updateStats(data);
            renderJoinCost(data.join_cost);
            joinCostPanel.style.display = 'block';
        } else {
            alert(`Error: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Query error:', error);
        alert('Failed to execute query. Is the server running?');
    } finally {
        executeBtn.disabled = false;
        executeBtn.innerHTML = '<i class="bi bi-play-fill"></i> Execute Hybrid Query';
    }
}

// ============================================================
// Render Functions
// ============================================================

function renderResults(data) {
    const results = data.results;
    resultsCount.textContent = `${results.length} results`;

    if (results.length === 0) {
        resultsBody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center text-muted py-5">
                    <i class="bi bi-search fs-1 d-block mb-2"></i>
                    No results found. Try different query terms or increase max distance.
                </td>
            </tr>
        `;
        return;
    }

    resultsBody.innerHTML = results.map((r, i) => {
        const p = r.patient;
        const dist = r.graph_distance !== null ? r.graph_distance : '-';
        const distClass = getDistanceClass(r.graph_distance);
        const partitionClass = `partition-${r.partition_id ?? 0}`;
        const combinedClass = getScoreClass(r.combined_score);

        return `
            <tr class="result-row" data-index="${i}" style="cursor: pointer;">
                <td><strong>${i + 1}</strong></td>
                <td><code>${p.patient_id}</code></td>
                <td><small>${escapeHtml(p.chief_complaint.substring(0, 60))}${p.chief_complaint.length > 60 ? '...' : ''}</small></td>
                <td><span class="badge bg-secondary">${p.department}</span></td>
                <td>
                    <span class="badge ${getSeverityClass(p.severity)}">${p.severity}/5</span>
                </td>
                <td>
                    ${r.graph_distance !== null
                        ? `<span class="badge ${distClass}">${r.graph_distance}</span>`
                        : '<span class="text-muted">-</span>'
                    }
                </td>
                <td><span class="score-medium">${r.text_score.toFixed(3)}</span></td>
                <td><span class="score-medium">${r.graph_importance.toFixed(3)}</span></td>
                <td><span class="badge ${combinedClass}">${r.combined_score.toFixed(3)}</span></td>
                <td><span class="badge ${partitionClass}">P${r.partition_id ?? 0}</span></td>
            </tr>
            <tr class="detail-row" id="detail-${i}" style="display: none;">
                <td colspan="10" class="p-3 patient-detail-row">
                    ${renderPatientDetail(p, r)}
                </td>
            </tr>
        `;
    }).join('');

    // Add click handlers for expanding details
    document.querySelectorAll('.result-row').forEach(row => {
        row.addEventListener('click', () => {
            const idx = row.dataset.index;
            const detailRow = document.getElementById(`detail-${idx}`);
            const isVisible = detailRow.style.display !== 'none';
            // Hide all other detail rows
            document.querySelectorAll('.detail-row').forEach(r => r.style.display = 'none');
            // Toggle this one
            detailRow.style.display = isVisible ? 'none' : 'table-row';
        });
    });
}

function renderPatientDetail(p, r) {
    return `
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">Patient ID</div>
                <div class="detail-value"><code>${p.patient_id}</code></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Age / Gender</div>
                <div class="detail-value">${p.age} / ${p.gender}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Admission Date</div>
                <div class="detail-value">${p.admission_date}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Department</div>
                <div class="detail-value"><span class="badge bg-secondary">${p.department}</span></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Severity</div>
                <div class="detail-value"><span class="badge ${getSeverityClass(p.severity)}">${p.severity}/5</span></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Initial Diagnosis</div>
                <div class="detail-value"><strong>${p.initial_diagnosis}</strong></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Graph Distance</div>
                <div class="detail-value">${r.distance_label || '-'}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Partition</div>
                <div class="detail-value"><span class="badge partition-${r.partition_id ?? 0}">P${r.partition_id ?? 0}</span></div>
            </div>
        </div>
        <div class="mt-2">
            <div class="detail-item">
                <div class="detail-label">Chief Complaint</div>
                <div class="detail-value">${escapeHtml(p.chief_complaint)}</div>
            </div>
        </div>
        <div class="mt-2">
            <div class="detail-item">
                <div class="detail-label">Full Symptoms</div>
                <div class="detail-value"><small>${escapeHtml(p.symptoms)}</small></div>
            </div>
        </div>
        <div class="mt-2">
            <div class="detail-item">
                <div class="detail-label">Medical History</div>
                <div class="detail-value"><small>${escapeHtml(p.medical_history)}</small></div>
            </div>
        </div>
        <div class="mt-2">
            <div class="detail-item">
                <div class="detail-label">Medications</div>
                <div class="detail-value"><small>${escapeHtml(p.current_medications)}</small></div>
            </div>
        </div>
        <div class="mt-3 border-top pt-2">
            <div class="d-flex gap-4">
                <div><span class="text-muted small">Text Score:</span> <strong class="score-medium">${r.text_score.toFixed(4)}</strong></div>
                <div><span class="text-muted small">Graph Importance:</span> <strong class="score-medium">${r.graph_importance.toFixed(4)}</strong></div>
                <div><span class="text-muted small">Combined Score:</span> <strong>${r.combined_score.toFixed(4)}</strong></div>
            </div>
        </div>
    `;
}

function renderJoinCost(joinCost) {
    const tierClass = `cost-tier-${joinCost.cost_tier.toLowerCase()}`;
    const tierIcon = joinCost.cost_tier === 'LOW' ? 'check-circle' :
                     joinCost.cost_tier === 'MEDIUM' ? 'exclamation-circle' : 'x-circle';

    joinCostMetrics.innerHTML = `
        <div class="col-md-3">
            <div class="border rounded p-2">
                <div class="text-muted small">Doc Scan Cost</div>
                <div class="fw-bold">${joinCost.document_scan_cost.toFixed(4)} ops</div>
                <div class="text-muted small">${joinCost.document_scan_count} docs</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="border rounded p-2">
                <div class="text-muted small">Graph Traversal Cost</div>
                <div class="fw-bold">${joinCost.graph_traversal_cost.toFixed(4)} ops</div>
                <div class="text-muted small">${joinCost.graph_traversal_nodes} nodes</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="border rounded p-2">
                <div class="text-muted small">Join Operation Cost</div>
                <div class="fw-bold">${joinCost.join_operation_cost.toFixed(4)} ops</div>
                <div class="text-muted small">${joinCost.join_operations} join ops</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="border rounded p-2">
                <div class="text-muted small">Network Transfer Cost</div>
                <div class="fw-bold">${joinCost.network_transfer_cost.toFixed(4)}</div>
                <div class="text-muted small">${joinCost.partition_access_count} partitions</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-2">
                <div class="text-muted small">Edge-Cut Ratio</div>
                <div class="fw-bold">${(joinCost.edge_cut_ratio * 100).toFixed(2)}%</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-2">
                <div class="text-muted small">Total Latency</div>
                <div class="fw-bold">${joinCost.total_latency_ms.toFixed(2)} ms</div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="border rounded p-2">
                <div class="text-muted small">Cost Tier</div>
                <div class="fw-bold ${tierClass}">
                    <i class="bi bi-${tierIcon}"></i> ${joinCost.cost_tier}
                </div>
            </div>
        </div>
    `;

    document.getElementById('joinCostSummary').innerHTML = `
        <div class="alert alert-secondary mb-0">
            <i class="bi bi-info-circle"></i>
            <strong>Cost Summary:</strong> ${joinCost.cost_summary}
        </div>
    `;
}

function updateStats(data) {
    statResults.textContent = data.total_results;
    statTime.textContent = data.execution_time_ms.toFixed(1);
    statPartitions.textContent = data.partitions_accessed.length;

    const tier = data.join_cost.cost_tier;
    statCost.textContent = tier;
    statCost.className = `stat-value cost-tier-${tier.toLowerCase()}`;
}

// ============================================================
// Helper Functions
// ============================================================

function getDistanceClass(dist) {
    if (dist === null || dist === undefined) return '';
    if (dist === 0) return 'distance-direct';
    if (dist === 1) return 'distance-1';
    if (dist === 2) return 'distance-2';
    return 'distance-3';
}

function getScoreClass(score) {
    if (score >= 0.7) return 'bg-success';
    if (score >= 0.4) return 'bg-warning text-dark';
    return 'bg-secondary';
}

function getSeverityClass(severity) {
    if (severity >= 4) return 'bg-danger';
    if (severity >= 3) return 'bg-warning text-dark';
    return 'bg-secondary';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function downloadResults() {
    if (currentResults.length === 0) {
        alert('No results to download');
        return;
    }

    const data = currentResults.map((r, i) => ({
        rank: i + 1,
        patient_id: r.patient.patient_id,
        chief_complaint: r.patient.chief_complaint,
        department: r.patient.department,
        severity: r.patient.severity,
        initial_diagnosis: r.patient.initial_diagnosis,
        graph_distance: r.graph_distance,
        distance_label: r.distance_label,
        text_score: r.text_score,
        graph_importance: r.graph_importance,
        combined_score: r.combined_score,
        partition_id: r.partition_id,
    }));

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hybrid_query_results_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// ============================================================
// Initialization
// ============================================================

// Check server health on load
fetch(`${API_BASE}/api/health`)
    .then(r => r.json())
    .then(data => {
        console.log('Server health:', data.status);
    })
    .catch(err => {
        console.warn('Server not reachable:', err);
    });
