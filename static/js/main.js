// Load printers list
function loadPrinters() {
    fetch('/printers')
        .then(response => response.json())
        .then(data => {
            displayPrinters(data);
            populatePrinterSelect(data);
        })
        .catch(error => {
            console.error('Error loading printers:', error);
            document.getElementById('printers-container').innerHTML = '<p>Error loading printers</p>';
        });
}

// Display printers
function displayPrinters(printers) {
    const container = document.getElementById('printers-container');

    if (!printers || printers.length === 0) {
        container.innerHTML = '<p>No printers</p>';
        return;
    }

    container.innerHTML = printers.map(printer => `
        <div class="printer-card">
            <h3>${printer.name || 'Unknown Printer'}</h3>
            <div class="printer-info">
                <strong>Model:</strong> ${printer.model || 'Not specified'}
            </div>
            <div class="printer-info">
                <strong>IP Address:</strong> ${printer.ip_address || 'Not specified'}
            </div>
            <div class="printer-info">
                <strong>Status:</strong> 
                <span class="status-badge status-${printer.status}">${printer.status === 'online' ? 'Online' : 'Offline'}</span>
            </div>
            <div class="ink-level">
                <strong>Ink Level:</strong> ${printer.ink_level || 0}%
                <div class="ink-bar">
                    <div class="ink-fill" style="width: ${printer.ink_level || 0}%"></div>
                </div>
            </div>
        </div>
    `).join('');
}

// Populate printer select in ticket form
function populatePrinterSelect(printers) {
    const select = document.getElementById('ticket-printer');
    if (!select) return;

    select.innerHTML = '<option value="">Select Printer</option>' +
        printers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
}

// Pagination variables
let currentTicketPage = 1;
let ticketsData = [];
let hasMoreTickets = true;

// Load tickets
function loadTickets(reset = false) {
    if (reset) {
        currentTicketPage = 1;
        ticketsData = [];
        hasMoreTickets = true;
    }

    const statusFilter = document.getElementById('status-filter')?.value || '';
    const priorityFilter = document.getElementById('priority-filter')?.value || '';
    const ticketTypeFilter = document.getElementById('ticket-type-filter')?.value || '';

    let url = '/tickets';
    const params = [];
    if (statusFilter) params.push(`status=${statusFilter}`);
    if (priorityFilter) params.push(`priority=${priorityFilter}`);
    if (ticketTypeFilter) params.push(`ticket_type=${ticketTypeFilter}`);
    params.push(`page=${currentTicketPage}`);
    params.push(`per_page=10`);
    if (params.length > 0) url += '?' + params.join('&');

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (reset) {
                ticketsData = data.tickets || [];
            } else {
                ticketsData = ticketsData.concat(data.tickets || []);
            }
            hasMoreTickets = data.has_more || false;
            displayTickets(ticketsData);
            updateLoadMoreButton();
        })
        .catch(error => {
            console.error('Error loading tickets:', error);
            document.getElementById('tickets-container').innerHTML = '<p>Error loading tickets</p>';
        });
}

// Display tickets
function displayTickets(tickets) {
    const container = document.getElementById('tickets-container');

    if (!tickets || tickets.length === 0) {
        container.innerHTML = '<p>No tickets</p>';
        return;
    }

    const ticketsList = tickets.map(ticket => `
        <div class="ticket-card" onclick="window.location.href='/ticket/${ticket.id}'">
            <h3><i class="fas fa-ticket-alt"></i> ${ticket.title || 'No title'}</h3>
            <p>${ticket.description ? (ticket.description.length > 100 ? ticket.description.substring(0, 100) + '...' : ticket.description) : 'No description'}</p>
            <div class="ticket-meta">
                <span class="status-badge status-${ticket.status.toLowerCase().replace(' ', '-')}"><i class="fas fa-circle"></i> ${getStatusText(ticket.status)}</span>
                <span class="priority-badge priority-${ticket.priority.toLowerCase()}"><i class="fas fa-exclamation-circle"></i> ${getPriorityText(ticket.priority)}</span>
                ${ticket.ticket_type ? `<span class="ticket-type-badge"><i class="fas fa-tag"></i> ${getTicketTypeText(ticket.ticket_type)}</span>` : ''}
                ${ticket.device_name ? `<span><i class="fas fa-desktop"></i> ${ticket.device_name}</span>` : ''}
                ${ticket.printer_name ? `<span><i class="fas fa-print"></i> ${ticket.printer_name}</span>` : ''}
                ${ticket.affected_users_count > 1 ? `<span><i class="fas fa-users"></i> ${ticket.affected_users_count} users</span>` : ''}
                ${ticket.has_ai_response ? `<span class="ai-badge"><i class="fas fa-robot"></i> AI Response Available</span>` : ''}
                <span><i class="fas fa-calendar"></i> ${formatDate(ticket.created_at)}</span>
            </div>
        </div>
    `).join('');

    container.innerHTML = '<div class="tickets-list">' + ticketsList + '</div>';

    // Add or update "Load More" button
    const existingBtn = document.getElementById('load-more-tickets');
    if (existingBtn) {
        existingBtn.remove();
    }

    if (hasMoreTickets) {
        const btnContainer = document.createElement('div');
        btnContainer.className = 'load-more-container';
        btnContainer.innerHTML = `
            <button id="load-more-tickets" class="btn-secondary" onclick="loadMoreTickets()">
                <i class="fas fa-chevron-down"></i> Load More
            </button>
        `;
        container.appendChild(btnContainer);
    }
}

// Update "Load More" button
function updateLoadMoreButton() {
    const loadMoreBtn = document.getElementById('load-more-tickets');
    if (loadMoreBtn) {
        if (hasMoreTickets) {
            loadMoreBtn.style.display = 'block';
        } else {
            loadMoreBtn.style.display = 'none';
        }
    }
}

// Load more tickets
function loadMoreTickets() {
    currentTicketPage++;
    loadTickets(false);
}

// Reset tickets when filters change
function resetTickets() {
    loadTickets(true);
}

// Load all tickets for statistics
function loadAllTicketsForStats() {
    fetch('/tickets?per_page=1000')
        .then(response => response.json())
        .then(data => {
            const allTickets = data.tickets || data || [];
            updateStats(allTickets);
        })
        .catch(error => {
            console.error('Error loading tickets for stats:', error);
        });
}

// Update statistics
function updateStats(tickets) {
    if (!tickets || !Array.isArray(tickets)) {
        console.error('Invalid tickets data:', tickets);
        return;
    }

    const today = new Date().toISOString().split('T')[0];
    const todayTickets = tickets.filter(t => t.created_at && t.created_at.startsWith(today));
    const openTickets = tickets.filter(t => t.status === 'Open');
    const inProgressTickets = tickets.filter(t => t.status === 'In Progress');
    const resolvedTickets = tickets.filter(t => t.status === 'Resolved');
    const highPriorityTickets = tickets.filter(t => t.priority === 'High' || t.priority === 'Critical');

    const openCountEl = document.getElementById('open-tickets-count');
    const todayCountEl = document.getElementById('today-tickets-count');
    const inProgressCountEl = document.getElementById('in-progress-count');
    const resolvedCountEl = document.getElementById('resolved-count');
    const highPriorityCountEl = document.getElementById('high-priority-count');
    const avgTimeEl = document.getElementById('avg-resolution-time');

    if (openCountEl) openCountEl.textContent = openTickets.length;
    if (todayCountEl) todayCountEl.textContent = todayTickets.length;
    if (inProgressCountEl) inProgressCountEl.textContent = inProgressTickets.length;
    if (resolvedCountEl) resolvedCountEl.textContent = resolvedTickets.length;
    if (highPriorityCountEl) highPriorityCountEl.textContent = highPriorityTickets.length;

    // Calculate average resolution time
    const resolved = tickets.filter(t => t.status === 'Resolved' && t.created_at && t.updated_at);
    if (resolved.length > 0 && avgTimeEl) {
        const totalHours = resolved.reduce((sum, t) => {
            const created = new Date(t.created_at);
            const updated = new Date(t.updated_at);
            return sum + (updated - created) / (1000 * 60 * 60);
        }, 0);
        const avgHours = Math.round(totalHours / resolved.length);
        avgTimeEl.textContent = avgHours + ' hours';
    } else if (avgTimeEl) {
        avgTimeEl.textContent = '-';
    }
}

// Show new ticket form
function showNewTicketForm() {
    document.getElementById('new-ticket-modal').style.display = 'flex';
    loadPrinters(); // To ensure printer list is updated
}

// Close new ticket form
function closeNewTicketForm() {
    document.getElementById('new-ticket-modal').style.display = 'none';
    document.getElementById('new-ticket-form').reset();
    document.getElementById('ai-response-preview').style.display = 'none';
    document.getElementById('ai-priority-suggestion').style.display = 'none';
    updateTicketType(); // Reset printer field display
}

// Update ticket type
function updateTicketType() {
    const ticketType = document.getElementById('ticket-type').value;
    const printerGroup = document.getElementById('printer-select-group');
    
    if (ticketType === 'printer') {
        printerGroup.style.display = 'block';
        document.getElementById('ticket-printer').required = false;
    } else {
        printerGroup.style.display = 'none';
        document.getElementById('ticket-printer').value = '';
    }
    
    updateAIPriority();
}

// Submit new ticket
function submitNewTicket(event) {
    event.preventDefault();

    const formData = {
        ticket_type: document.getElementById('ticket-type').value,
        printer_id: parseInt(document.getElementById('ticket-printer').value) || null,
        device_name: document.getElementById('ticket-device-name').value || null,
        affected_users_count: parseInt(document.getElementById('ticket-affected-users').value) || 1,
        title: document.getElementById('ticket-title').value,
        description: document.getElementById('ticket-description').value,
        priority: document.getElementById('ticket-priority').value || '',
        reporter_email: document.getElementById('ticket-email').value || null
    };

    if (!formData.title || !formData.description) {
        alert('Please fill all required fields');
        return;
    }

    fetch('/tickets', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                // Display AI response to user
                if (data.ai_response) {
                    let message = 'Ticket created successfully!\n\n';
                    message += 'Automatic Initial Response:\n';
                    message += data.ai_response.initial_response + '\n\n';
                    message += 'Troubleshooting Steps:\n';
                    message += data.ai_response.troubleshooting_steps + '\n\n';
                    message += 'Common Solutions:\n';
                    message += data.ai_response.common_solutions;
                    alert(message);
                } else {
                    alert('Ticket created successfully');
                }
                closeNewTicketForm();
                loadTickets(true);
            } else {
                alert('Error creating ticket');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error creating ticket');
        });
}

// Helper functions
function getStatusText(status) {
    const statusMap = {
        'Open': 'Open',
        'In Progress': 'In Progress',
        'Resolved': 'Resolved'
    };
    return statusMap[status] || status;
}

function getPriorityText(priority) {
    const priorityMap = {
        'Low': 'Low',
        'Medium': 'Medium',
        'High': 'High',
        'Critical': 'Critical'
    };
    return priorityMap[priority] || priority;
}

function getTicketTypeText(type) {
    const typeMap = {
        'printer': 'Printers',
        'network': 'Networks',
        'hardware': 'Hardware',
        'software': 'Software',
        'other': 'Other'
    };
    return typeMap[type] || type;
}

function formatDate(dateString) {
    if (!dateString) return 'Not specified';
    const date = new Date(dateString);
    // Use Gregorian date only
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    };
    return date.toLocaleDateString('en-US', options).replace(',', '');
}

// Close modal when clicking outside
window.onclick = function (event) {
    const modal = document.getElementById('new-ticket-modal');
    if (event.target === modal) {
        closeNewTicketForm();
    }
}

// Refresh printers
function refreshPrinters() {
    loadPrinters();
}

// Load analytics
function loadAnalytics() {
    fetch('/tickets?per_page=1000')
        .then(response => response.json())
        .then(data => {
            const tickets = data.tickets || data || [];
            createPriorityChart(tickets);
            createStatusChart(tickets);
            createTimelineChart(tickets);
        })
        .catch(error => {
            console.error('Error loading analytics:', error);
        });
}

// Create priority chart
function createPriorityChart(tickets) {
    const ctx = document.getElementById('priorityChart');
    if (!ctx) return;

    const priorityCounts = {
        'Low': tickets.filter(t => t.priority === 'Low').length,
        'Medium': tickets.filter(t => t.priority === 'Medium').length,
        'High': tickets.filter(t => t.priority === 'High').length,
        'Critical': tickets.filter(t => t.priority === 'Critical').length
    };

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Low', 'Medium', 'High', 'Critical'],
            datasets: [{
                data: [priorityCounts.Low, priorityCounts.Medium, priorityCounts.High, priorityCounts.Critical],
                backgroundColor: ['#3b82f6', '#f59e0b', '#ef4444', '#dc2626'],
                borderWidth: 2,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e2e8f0',
                        font: {
                            family: 'IBMPlexSansArabic'
                        }
                    }
                }
            }
        }
    });
}

// Create status chart
function createStatusChart(tickets) {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;

    const statusCounts = {
        'Open': tickets.filter(t => t.status === 'Open').length,
        'In Progress': tickets.filter(t => t.status === 'In Progress').length,
        'Resolved': tickets.filter(t => t.status === 'Resolved').length
    };

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Open', 'In Progress', 'Resolved'],
            datasets: [{
                data: [statusCounts.Open, statusCounts['In Progress'], statusCounts.Resolved],
                backgroundColor: ['#3b82f6', '#f59e0b', '#10b981'],
                borderWidth: 2,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e2e8f0',
                        font: {
                            family: 'IBMPlexSansArabic'
                        }
                    }
                }
            }
        }
    });
}

// Create timeline chart
function createTimelineChart(tickets) {
    const ctx = document.getElementById('timelineChart');
    if (!ctx) return;

    // Group tickets by last 7 days
    const last7Days = [];
    const counts = [];

    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];

        const dayTickets = tickets.filter(t => t.created_at && t.created_at.startsWith(dateStr));
        const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
        const dayNum = date.getDate();
        last7Days.push(`${dayName} ${dayNum}`);
        counts.push(dayTickets.length);
    }

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: last7Days,
            datasets: [{
                label: 'Number of Tickets',
                data: counts,
                borderColor: '#60a5fa',
                backgroundColor: 'rgba(96, 165, 250, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: '#334155'
                    }
                },
                x: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: '#334155'
                    }
                }
            }
        }
    });
}

// Generate report and download as CSV
function generateReport(type) {
    const btn = event?.target?.closest('button');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    }

    const resetBtn = () => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-download"></i> Download Report';
        }
    };

    if (type === 'tickets') {
        fetch('/tickets?per_page=1000')
            .then(r => r.json())
            .then(data => {
                const tickets = data.tickets || [];
                const headers = ['ID', 'Title', 'Type', 'Priority', 'Status', 'Device', 'Printer', 'Affected Users', 'Reporter', 'Created', 'Updated'];
                const rows = tickets.map(t => [
                    t.id, t.title, t.ticket_type || '', t.priority, t.status,
                    t.device_name || '', t.printer_name || '', t.affected_users_count || 1,
                    t.reporter_email || '', t.created_at || '', t.updated_at || ''
                ]);
                downloadCSV('tickets_report.csv', headers, rows);
                resetBtn();
            })
            .catch(err => { console.error(err); alert('Error generating tickets report'); resetBtn(); });
    } else if (type === 'printers') {
        fetch('/printers')
            .then(r => r.json())
            .then(printers => {
                const headers = ['ID', 'Name', 'Model', 'IP Address', 'Status', 'Ink Level %', 'Last Seen'];
                const rows = printers.map(p => [
                    p.id, p.name, p.model || '', p.ip_address || '', p.status,
                    p.ink_level || 0, p.last_seen || ''
                ]);
                downloadCSV('printers_report.csv', headers, rows);
                resetBtn();
            })
            .catch(err => { console.error(err); alert('Error generating printers report'); resetBtn(); });
    } else if (type === 'performance') {
        Promise.all([
            fetch('/tickets?per_page=1000').then(r => r.json()),
            fetch('/printers').then(r => r.json()),
            fetch('/devices').then(r => r.json())
        ])
            .then(([ticketData, printers, devices]) => {
                const tickets = ticketData.tickets || [];
                const open = tickets.filter(t => t.status === 'Open').length;
                const inProgress = tickets.filter(t => t.status === 'In Progress').length;
                const resolved = tickets.filter(t => t.status === 'Resolved').length;
                const critical = tickets.filter(t => t.priority === 'Critical').length;
                const high = tickets.filter(t => t.priority === 'High').length;
                const onlinePrinters = printers.filter(p => p.status === 'online').length;
                const offlinePrinters = printers.filter(p => p.status === 'offline').length;
                const onlineDevices = devices.filter(d => d.status === 'online').length;

                const headers = ['Metric', 'Value'];
                const rows = [
                    ['Total Tickets', tickets.length],
                    ['Open Tickets', open],
                    ['In Progress', inProgress],
                    ['Resolved', resolved],
                    ['Critical Priority', critical],
                    ['High Priority', high],
                    ['Total Printers', printers.length],
                    ['Online Printers', onlinePrinters],
                    ['Offline Printers', offlinePrinters],
                    ['Total Devices', devices.length],
                    ['Online Devices', onlineDevices],
                    ['Report Generated', new Date().toISOString()]
                ];
                downloadCSV('performance_report.csv', headers, rows);
                resetBtn();
            })
            .catch(err => { console.error(err); alert('Error generating performance report'); resetBtn(); });
    }
}

function downloadCSV(filename, headers, rows) {
    const escapeCell = (cell) => {
        const str = String(cell ?? '').replace(/"/g, '""');
        return `"${str}"`;
    };
    const csv = [headers.map(escapeCell).join(','), ...rows.map(r => r.map(escapeCell).join(','))].join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
}

// Load smart alerts
function loadAlerts() {
    fetch('/alerts?unread_only=true')
        .then(response => response.json())
        .then(data => {
            displayAlerts(data);
        })
        .catch(error => {
            console.error('Error loading alerts:', error);
        });
}

// Display alerts
function displayAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<p class="no-data">No new alerts</p>';
        return;
    }

    container.innerHTML = '<div class="alerts-list">' + alerts.map(alert => {
        const severityClass = `alert-severity-${alert.severity}`;
        const icon = getAlertIcon(alert.alert_type);
        return `
            <div class="alert-item ${severityClass}" onclick="markAlertRead(${alert.id})">
                <div class="alert-icon">${icon}</div>
                <div class="alert-content">
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">${formatDate(alert.created_at)}</div>
                </div>
                <div class="alert-actions">
                    <i class="fas fa-times" onclick="event.stopPropagation(); markAlertRead(${alert.id})"></i>
                </div>
            </div>
        `;
    }).join('') + '</div>';
}

function getAlertIcon(alertType) {
    const icons = {
        'low_ink': '<i class="fas fa-tint"></i>',
        'offline': '<i class="fas fa-wifi-slash"></i>',
        'high_priority': '<i class="fas fa-exclamation-triangle"></i>',
        'maintenance_due': '<i class="fas fa-wrench"></i>'
    };
    return icons[alertType] || '<i class="fas fa-bell"></i>';
}

function markAlertRead(alertId) {
    fetch(`/alerts/${alertId}/read`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            loadAlerts();
        })
        .catch(error => {
            console.error('Error marking alert as read:', error);
        });
}

// Load ink depletion predictions
function loadInkPredictions() {
    fetch('/predictions/ink')
        .then(response => response.json())
        .then(data => {
            displayInkPredictions(data);
        })
        .catch(error => {
            console.error('Error loading ink predictions:', error);
        });
}

// Display ink depletion predictions
function displayInkPredictions(predictions) {
    const container = document.getElementById('predictions-container');
    if (!container) return;

    if (!predictions || predictions.length === 0) {
        container.innerHTML = '<p class="no-data">No predictions available</p>';
        return;
    }

    container.innerHTML = predictions.map(pred => {
        const daysLeft = pred.days_until_depletion;
        const urgencyClass = daysLeft < 7 ? 'urgent' : daysLeft < 14 ? 'warning' : 'normal';
        return `
            <div class="prediction-card ${urgencyClass}">
                <h3><i class="fas fa-print"></i> ${pred.printer_name}</h3>
                <div class="prediction-info">
                    <div class="prediction-item">
                        <strong>Current Level:</strong> ${pred.current_level}%
                    </div>
                    <div class="prediction-item">
                        <strong>Predicted Date:</strong> ${formatDate(pred.predicted_depletion_date)}
                    </div>
                    <div class="prediction-item">
                        <strong>Days Remaining:</strong> ${daysLeft} days
                    </div>
                    <div class="prediction-item">
                        <strong>Confidence Score:</strong> ${(pred.confidence * 100).toFixed(0)}%
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Load maintenance schedule
function loadMaintenanceSchedule() {
    fetch('/maintenance/schedule?upcoming=true')
        .then(response => response.json())
        .then(data => {
            displayMaintenanceSchedule(data);
        })
        .catch(error => {
            console.error('Error loading maintenance schedule:', error);
        });
}

// Display maintenance schedule
function displayMaintenanceSchedule(schedules) {
    const container = document.getElementById('maintenance-container');
    if (!container) return;

    if (!schedules || schedules.length === 0) {
        container.innerHTML = '<p class="no-data">No scheduled maintenance</p>';
        return;
    }

    container.innerHTML = '<div class="maintenance-list">' + schedules.map(schedule => {
        const typeText = {
            'cleaning': 'Cleaning',
            'inspection': 'Inspection',
            'repair': 'Repair',
            'replacement': 'Replacement'
        }[schedule.maintenance_type] || schedule.maintenance_type;

        return `
            <div class="maintenance-item">
                <div class="maintenance-icon">
                    <i class="fas fa-wrench"></i>
                </div>
                <div class="maintenance-content">
                    <h4>${typeText}</h4>
                    <p>${formatDate(schedule.scheduled_date)}</p>
                    ${schedule.notes ? `<p class="maintenance-notes">${schedule.notes}</p>` : ''}
                </div>
                <div class="maintenance-status">
                    <span class="status-badge status-${schedule.status}">${schedule.status === 'scheduled' ? 'Scheduled' : schedule.status === 'completed' ? 'Completed' : 'Cancelled'}</span>
                </div>
            </div>
        `;
    }).join('') + '</div>';
}

// Show maintenance scheduling form
function showMaintenanceForm() {
    document.getElementById('maintenance-modal').style.display = 'flex';
    loadPrinters(); // To ensure printer list is updated
    const printerSelect = document.getElementById('maintenance-printer');
    if (printerSelect) {
        fetch('/printers')
            .then(response => response.json())
            .then(printers => {
                printerSelect.innerHTML = '<option value="">Select Printer</option>' +
                    printers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
            });
    }
}

// Close maintenance scheduling form
function closeMaintenanceForm() {
    document.getElementById('maintenance-modal').style.display = 'none';
    document.getElementById('maintenance-form').reset();
}

// Submit maintenance schedule
function submitMaintenance(event) {
    event.preventDefault();

    const formData = {
        printer_id: parseInt(document.getElementById('maintenance-printer').value),
        maintenance_type: document.getElementById('maintenance-type').value,
        scheduled_date: document.getElementById('maintenance-date').value,
        notes: document.getElementById('maintenance-notes').value || null
    };

    fetch('/maintenance/schedule', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert('Maintenance scheduled successfully');
                closeMaintenanceForm();
                loadMaintenanceSchedule();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error scheduling maintenance');
        });
}

// Update priority using AI
function updateAIPriority() {
    const title = document.getElementById('ticket-title')?.value || '';
    const description = document.getElementById('ticket-description')?.value || '';
    const printerId = document.getElementById('ticket-printer')?.value || '';
    const ticketType = document.getElementById('ticket-type')?.value || 'printer';
    const affectedUsers = document.getElementById('ticket-affected-users')?.value || 1;
    const deviceName = document.getElementById('ticket-device-name')?.value || '';

    if (!title || !description) {
        document.getElementById('ai-response-preview')?.style.setProperty('display', 'none');
        return;
    }

    fetch('/analytics/ai-priority', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            title: title,
            description: description,
            printer_id: printerId || null,
            ticket_type: ticketType,
            affected_users_count: parseInt(affectedUsers) || 1,
            device_name: deviceName || null
        })
    })
        .then(response => response.json())
        .then(data => {
            const suggestionDiv = document.getElementById('ai-priority-suggestion');
            const suggestionText = document.getElementById('ai-priority-text');
            const aiResponsePreview = document.getElementById('ai-response-preview');
            const aiResponseContent = document.getElementById('ai-response-content');

            if (suggestionDiv && suggestionText) {
                const priorityText = {
                    'Low': 'Low',
                    'Medium': 'Medium',
                    'High': 'High',
                    'Critical': 'Critical'
                }[data.priority] || data.priority;

                suggestionText.textContent = `Suggested Priority: ${priorityText} (AI Score: ${data.score}/100) - Category: ${data.category} (Confidence: ${(data.confidence * 100).toFixed(0)}%)`;
                suggestionDiv.style.display = 'block';

                // Update dropdown
                const prioritySelect = document.getElementById('ticket-priority');
                if (prioritySelect && prioritySelect.value === '') {
                    prioritySelect.value = data.priority;
                }
            }

            // Display AI response preview
            if (aiResponsePreview && aiResponseContent && data.ai_response_preview) {
                aiResponseContent.textContent = data.ai_response_preview;
                aiResponsePreview.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error calculating AI priority:', error);
        });
}

// Analyze printer patterns
function analyzePrinterPatterns(printerId) {
    const container = document.getElementById('patterns-container');
    if (container) container.innerHTML = '<p>Loading analysis...</p>';

    fetch(`/analytics/patterns/${printerId}`)
        .then(response => response.json())
        .then(data => {
            displayPatterns(data, printerId);
        })
        .catch(error => {
            console.error('Error loading patterns:', error);
            if (container) container.innerHTML = '<p class="no-data">Error loading pattern analysis</p>';
        });
}

// Load patterns section with printer selector and overview
function loadPatternsSection() {
    fetch('/printers')
        .then(r => r.json())
        .then(printers => {
            const select = document.getElementById('pattern-printer-select');
            if (select) {
                select.innerHTML = '<option value="">All Printers (Overview)</option>' +
                    printers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
            }

            if (!printers || printers.length === 0) {
                const container = document.getElementById('patterns-container');
                if (container) container.innerHTML = '<p class="no-data">No printers available for analysis</p>';
                return;
            }

            loadAllPatternsOverview(printers);
        })
        .catch(error => {
            console.error('Error loading patterns section:', error);
        });
}

function onPatternPrinterChange(printerId) {
    if (!printerId) {
        fetch('/printers')
            .then(r => r.json())
            .then(printers => loadAllPatternsOverview(printers));
        return;
    }
    analyzePrinterPatterns(parseInt(printerId));
}

function loadAllPatternsOverview(printers) {
    const container = document.getElementById('patterns-container');
    if (!container) return;
    container.innerHTML = '<p>Loading analysis for all printers...</p>';

    Promise.all(
        printers.map(p =>
            fetch(`/analytics/patterns/${p.id}`)
                .then(r => r.json())
                .then(data => ({ printer: p, patterns: data }))
                .catch(() => ({ printer: p, patterns: null }))
        )
    ).then(results => {
        const categoryNames = {
            'hardware': 'Hardware Problems',
            'software': 'Software Problems',
            'network': 'Network Problems',
            'ink': 'Ink Problems',
            'paper': 'Paper Problems',
            'other': 'Other'
        };

        const cards = results.map(({ printer, patterns }) => {
            if (!patterns || patterns.message) {
                return `
                    <div class="pattern-card">
                        <h3><i class="fas fa-print"></i> ${printer.name}</h3>
                        <p class="no-data">Not enough ticket data (minimum 3 tickets required)</p>
                    </div>`;
            }

            const freqItems = Object.entries(patterns.issue_frequency || {}).map(([cat, count]) => {
                const pct = patterns.issue_percentages?.[cat] || 0;
                return `<li>${categoryNames[cat] || cat}: ${count} tickets (${pct}%)</li>`;
            }).join('');

            const priorityItems = Object.entries(patterns.priority_distribution || {}).map(([pri, pct]) =>
                `<li>${pri}: ${pct}%</li>`
            ).join('');

            return `
                <div class="pattern-card">
                    <h3><i class="fas fa-print"></i> ${printer.name}</h3>
                    <div class="pattern-stats">
                        <div class="pattern-stat">
                            <strong>Total Tickets</strong>
                            ${patterns.total_tickets}
                        </div>
                        <div class="pattern-stat">
                            <strong>Most Common Issue</strong>
                            ${categoryNames[patterns.most_common_issue] || patterns.most_common_issue || 'N/A'}
                        </div>
                    </div>
                    <div class="pattern-frequency">
                        <h4>Problem Distribution:</h4>
                        <ul>${freqItems || '<li>No categorized issues</li>'}</ul>
                    </div>
                    ${priorityItems ? `<div class="pattern-frequency"><h4>Priority Distribution:</h4><ul>${priorityItems}</ul></div>` : ''}
                    <button class="btn-secondary pattern-detail-btn" onclick="document.getElementById('pattern-printer-select').value='${printer.id}'; analyzePrinterPatterns(${printer.id})">
                        <i class="fas fa-search"></i> Detailed View
                    </button>
                </div>`;
        }).join('');

        container.innerHTML = cards || '<p class="no-data">No pattern data available</p>';
    });
}

// Display pattern analysis (single printer detailed view)
function displayPatterns(patterns, printerId) {
    const container = document.getElementById('patterns-container');
    if (!container) return;

    if (!patterns || patterns.message) {
        container.innerHTML = '<p class="no-data">Not enough data for analysis (minimum 3 tickets required for this printer)</p>';
        return;
    }

    const categoryNames = {
        'hardware': 'Hardware Problems',
        'software': 'Software Problems',
        'network': 'Network Problems',
        'ink': 'Ink Problems',
        'paper': 'Paper Problems',
        'other': 'Other'
    };

    const freqItems = Object.entries(patterns.issue_frequency || {}).map(([cat, count]) => {
        const pct = patterns.issue_percentages?.[cat] || 0;
        return `<li>${categoryNames[cat] || cat}: ${count} tickets (${pct}%)</li>`;
    }).join('');

    const priorityItems = Object.entries(patterns.priority_distribution || {}).map(([pri, pct]) =>
        `<li>${pri}: ${pct}%</li>`
    ).join('');

    const statusItems = Object.entries(patterns.status_distribution || {}).map(([st, pct]) =>
        `<li>${st}: ${pct}%</li>`
    ).join('');

    container.innerHTML = `
        <div class="pattern-card">
            <h3>Pattern Analysis - Printer #${printerId}</h3>
            <div class="pattern-stats">
                <div class="pattern-stat">
                    <strong>Total Tickets</strong>
                    ${patterns.total_tickets}
                </div>
                <div class="pattern-stat">
                    <strong>Most Common Issue</strong>
                    ${categoryNames[patterns.most_common_issue] || patterns.most_common_issue}
                </div>
            </div>
            <div class="pattern-frequency">
                <h4>Problem Distribution:</h4>
                <ul>${freqItems}</ul>
            </div>
            <div class="pattern-frequency">
                <h4>Priority Distribution:</h4>
                <ul>${priorityItems}</ul>
            </div>
            <div class="pattern-frequency">
                <h4>Status Distribution:</h4>
                <ul>${statusItems}</ul>
            </div>
            <button class="btn-secondary" onclick="document.getElementById('pattern-printer-select').value=''; onPatternPrinterChange('')">
                <i class="fas fa-arrow-left"></i> Back to Overview
            </button>
        </div>
    `;
}

// Load recent tickets for home page
function loadRecentTickets() {
    fetch('/tickets?per_page=5')
        .then(response => response.json())
        .then(data => {
            const tickets = data.tickets || [];
            displayRecentTickets(tickets);
        })
        .catch(error => {
            console.error('Error loading recent tickets:', error);
        });
}

// Display recent tickets
function displayRecentTickets(tickets) {
    const container = document.getElementById('recent-tickets-container');
    if (!container) return;

    if (!tickets || tickets.length === 0) {
        container.innerHTML = '<p class="no-data">No tickets</p>';
        return;
    }

    container.innerHTML = tickets.map(ticket => `
        <div class="ticket-card" onclick="window.location.href='/ticket/${ticket.id}'">
            <h3><i class="fas fa-ticket-alt"></i> ${ticket.title || 'No title'}</h3>
            <p>${ticket.description ? (ticket.description.length > 80 ? ticket.description.substring(0, 80) + '...' : ticket.description) : 'No description'}</p>
            <div class="ticket-meta">
                <span class="status-badge status-${ticket.status.toLowerCase().replace(' ', '-')}"><i class="fas fa-circle"></i> ${getStatusText(ticket.status)}</span>
                <span class="priority-badge priority-${ticket.priority.toLowerCase()}"><i class="fas fa-exclamation-circle"></i> ${getPriorityText(ticket.priority)}</span>
                <span><i class="fas fa-calendar"></i> ${formatDate(ticket.created_at)}</span>
            </div>
        </div>
    `).join('');
}

// Load recent printers and devices for home page
function loadRecentPrinters() {
    Promise.all([
        fetch('/printers').then(r => r.json()),
        fetch('/devices').then(r => r.json())
    ])
        .then(([printers, devices]) => {
            const allItems = [
                ...printers.slice(0, 3).map(p => ({...p, type: 'printer'})),
                ...devices.slice(0, 3).map(d => ({...d, type: 'device'}))
            ];
            displayRecentPrinters(allItems);
            displayRecentDevices(devices.slice(0, 6));
        })
        .catch(error => {
            console.error('Error loading recent printers/devices:', error);
        });
}

// Load devices
function loadDevices() {
    fetch('/devices')
        .then(response => response.json())
        .then(data => {
            displayDevices(data);
            populateDeviceSelect(data);
        })
        .catch(error => {
            console.error('Error loading devices:', error);
            document.getElementById('devices-container').innerHTML = '<p>Error loading devices</p>';
        });
}

// Display devices
function displayDevices(devices) {
    const container = document.getElementById('devices-container');
    if (!container) return;

    if (!devices || devices.length === 0) {
        container.innerHTML = '<p>No devices</p>';
        return;
    }

    const deviceTypeNames = {
        'server': 'Server',
        'network_device': 'Network Device',
        'workstation': 'Workstation',
        'printer': 'Printer',
        'software': 'Software'
    };

    container.innerHTML = devices.map(device => `
        <div class="device-card">
            <h3><i class="fas fa-${device.device_type === 'server' ? 'server' : device.device_type === 'network_device' ? 'network-wired' : 'desktop'}"></i> ${device.name || 'Unknown Device'}</h3>
            <div class="device-info">
                <strong>Type:</strong> ${deviceTypeNames[device.device_type] || device.device_type}
            </div>
            <div class="device-info">
                <strong>IP Address:</strong> ${device.ip_address || 'Not specified'}
            </div>
            ${device.location ? `<div class="device-info"><strong>Location:</strong> ${device.location}</div>` : ''}
            <div class="device-info">
                <strong>Status:</strong> 
                <span class="status-badge status-${device.status}">${device.status === 'online' ? 'Online' : device.status === 'offline' ? 'Offline' : device.status === 'warning' ? 'Warning' : 'Error'}</span>
            </div>
            ${device.last_seen ? `<div class="device-info"><strong>Last Seen:</strong> ${formatDate(device.last_seen)}</div>` : ''}
        </div>
    `).join('');
}

// Refresh devices
function refreshDevices() {
    loadDevices();
}

// Display recent devices
function displayRecentDevices(devices) {
    const container = document.getElementById('recent-devices-container');
    if (!container) return;

    if (!devices || devices.length === 0) {
        container.innerHTML = '<p class="no-data">No devices</p>';
        return;
    }

    const deviceTypeNames = {
        'server': 'Server',
        'network_device': 'Network Device',
        'workstation': 'Workstation',
        'printer': 'Printer',
        'software': 'Software'
    };

    container.innerHTML = devices.map(device => `
        <div class="device-card">
            <h3><i class="fas fa-${device.device_type === 'server' ? 'server' : device.device_type === 'network_device' ? 'network-wired' : 'desktop'}"></i> ${device.name || 'Unknown Device'}</h3>
            <div class="device-info">
                <strong><i class="fas fa-tag"></i> Type:</strong> ${deviceTypeNames[device.device_type] || device.device_type}
            </div>
            <div class="device-info">
                <strong><i class="fas fa-network-wired"></i> IP Address:</strong> ${device.ip_address || 'Not specified'}
            </div>
            ${device.location ? `<div class="device-info"><strong><i class="fas fa-map-marker-alt"></i> Location:</strong> ${device.location}</div>` : ''}
            <div class="device-info">
                <strong><i class="fas fa-power-off"></i> Status:</strong> 
                <span class="status-badge status-${device.status}">${device.status === 'online' ? 'Online' : device.status === 'offline' ? 'Offline' : device.status === 'warning' ? 'Warning' : 'Error'}</span>
            </div>
        </div>
    `).join('');
}

// Display recent printers and devices
function displayRecentPrinters(items) {
    const container = document.getElementById('recent-printers-container');
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = '<p class="no-data">No printers or devices</p>';
        return;
    }

    container.innerHTML = items.map(item => {
        if (item.type === 'printer') {
            return `
                <div class="printer-card">
                    <h3><i class="fas fa-print"></i> ${item.name || 'Unknown Printer'}</h3>
                    <div class="printer-info">
                        <strong><i class="fas fa-tag"></i> Model:</strong> ${item.model || 'Not specified'}
                    </div>
                    <div class="printer-info">
                        <strong><i class="fas fa-network-wired"></i> IP Address:</strong> ${item.ip_address || 'Not specified'}
                    </div>
                    <div class="printer-info">
                        <strong><i class="fas fa-power-off"></i> Status:</strong> 
                        <span class="status-badge status-${item.status}">${item.status === 'online' ? 'Online' : 'Offline'}</span>
                    </div>
                    <div class="ink-level">
                        <strong><i class="fas fa-tint"></i> Ink Level:</strong> ${item.ink_level || 0}%
                        <div class="ink-bar">
                            <div class="ink-fill" style="width: ${item.ink_level || 0}%"></div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            const deviceTypeNames = {
                'server': 'Server',
                'network_device': 'Network Device',
                'workstation': 'Workstation'
            };
            return `
                <div class="device-card">
                    <h3><i class="fas fa-${item.device_type === 'server' ? 'server' : item.device_type === 'network_device' ? 'network-wired' : 'desktop'}"></i> ${item.name || 'Unknown Device'}</h3>
                    <div class="device-info">
                        <strong><i class="fas fa-tag"></i> Type:</strong> ${deviceTypeNames[item.device_type] || item.device_type}
                    </div>
                    <div class="device-info">
                        <strong><i class="fas fa-network-wired"></i> IP Address:</strong> ${item.ip_address || 'Not specified'}
                    </div>
                    ${item.location ? `<div class="device-info"><strong><i class="fas fa-map-marker-alt"></i> Location:</strong> ${item.location}</div>` : ''}
                    <div class="device-info">
                        <strong><i class="fas fa-power-off"></i> Status:</strong> 
                        <span class="status-badge status-${item.status}">${item.status === 'online' ? 'Online' : item.status === 'offline' ? 'Offline' : item.status === 'warning' ? 'Warning' : 'Error'}</span>
                    </div>
                </div>
            `;
        }
    }).join('');
}

// Load recent alerts for home page
function loadRecentAlerts() {
    fetch('/alerts?unread_only=true')
        .then(response => response.json())
        .then(data => {
            const alerts = data.slice(0, 5);
            displayRecentAlerts(alerts);
        })
        .catch(error => {
            console.error('Error loading recent alerts:', error);
        });
}

// Display recent alerts
function displayRecentAlerts(alerts) {
    const container = document.getElementById('recent-alerts-container');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<p class="no-data">No new alerts</p>';
        return;
    }

    container.innerHTML = '<div class="alerts-list">' + alerts.map(alert => {
        const severityClass = `alert-severity-${alert.severity}`;
        const icon = getAlertIcon(alert.alert_type);
        return `
            <div class="alert-item ${severityClass}">
                <div class="alert-icon">${icon}</div>
                <div class="alert-content">
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">${formatDate(alert.created_at)}</div>
                </div>
            </div>
        `;
    }).join('') + '</div>';
}

// Load recent predictions for home page
function loadRecentPredictions() {
    fetch('/predictions/ink')
        .then(response => response.json())
        .then(data => {
            const predictions = data.slice(0, 3);
            displayRecentPredictions(predictions);
        })
        .catch(error => {
            console.error('Error loading recent predictions:', error);
        });
}

// Display recent predictions
function displayRecentPredictions(predictions) {
    const container = document.getElementById('recent-predictions-container');
    if (!container) return;

    if (!predictions || predictions.length === 0) {
        container.innerHTML = '<p class="no-data">No predictions available</p>';
        return;
    }

    container.innerHTML = predictions.map(pred => {
        const daysLeft = pred.days_until_depletion;
        const urgencyClass = daysLeft < 7 ? 'urgent' : daysLeft < 14 ? 'warning' : 'normal';
        return `
            <div class="prediction-card ${urgencyClass}">
                <h3><i class="fas fa-print"></i> ${pred.printer_name}</h3>
                <div class="prediction-info">
                    <div class="prediction-item">
                        <strong><i class="fas fa-tint"></i> Current Level:</strong> ${pred.current_level}%
                    </div>
                    <div class="prediction-item">
                        <strong><i class="fas fa-calendar"></i> Predicted Date:</strong> ${formatDate(pred.predicted_depletion_date)}
                    </div>
                    <div class="prediction-item">
                        <strong><i class="fas fa-clock"></i> Days Remaining:</strong> ${daysLeft} days
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Populate device datalist for ticket form
function populateDeviceSelect(devices) {
    const input = document.getElementById('ticket-device-name');
    if (!input || !devices) return;

    let datalist = document.getElementById('device-names-list');
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = 'device-names-list';
        input.setAttribute('list', 'device-names-list');
        input.parentNode.appendChild(datalist);
    }

    datalist.innerHTML = devices.map(d => `<option value="${d.name}">`).join('');
}

// Theme management
function toggleTheme(isDark) {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateChartColors(isDark);
}

function initTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    const isDark = saved === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    const toggle = document.getElementById('dark-mode-toggle');
    if (toggle) toggle.checked = isDark;
}

function updateChartColors(isDark) {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.color = isDark ? '#e2e8f0' : '#334155';
    Chart.defaults.borderColor = isDark ? '#334155' : '#e2e8f0';
}

// Add event listeners
document.addEventListener('DOMContentLoaded', function () {
    initTheme();

    const titleInput = document.getElementById('ticket-title');
    const descriptionInput = document.getElementById('ticket-description');

    if (titleInput) {
        titleInput.addEventListener('input', updateAIPriority);
    }
    if (descriptionInput) {
        descriptionInput.addEventListener('input', updateAIPriority);
    }
});

