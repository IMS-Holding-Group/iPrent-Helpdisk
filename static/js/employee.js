function switchPortalTab(tabId) {
    document.querySelectorAll('.portal-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    document.querySelectorAll('.portal-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === tabId + '-panel');
    });
    if (tabId === 'my-tickets') {
        loadEmployeeTickets();
    }
}

function updateEmployeeTicketType() {
    const ticketType = document.getElementById('emp-ticket-type').value;
    const printerGroup = document.getElementById('emp-printer-group');
    if (printerGroup) {
        printerGroup.style.display = ticketType === 'printer' ? 'block' : 'none';
    }
}

function loadEmployeePrinters() {
    fetch('/printers')
        .then(r => r.json())
        .then(printers => {
            const select = document.getElementById('emp-ticket-printer');
            if (!select) return;
            select.innerHTML = '<option value="">Select Printer</option>' +
                printers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        })
        .catch(err => console.error('Error loading printers:', err));
}

function loadEmployeeTickets() {
    const container = document.getElementById('employee-tickets-container');
    if (!container) return;
    container.innerHTML = '<p>Loading...</p>';

    fetch('/tickets?per_page=100')
        .then(r => r.json())
        .then(data => {
            const tickets = data.tickets || [];
            if (!tickets.length) {
                container.innerHTML = '<p class="no-data">You have not submitted any tickets yet</p>';
                return;
            }
            container.innerHTML = tickets.map(ticket => `
                <div class="ticket-card" onclick="window.location.href='/portal/ticket/${ticket.id}'">
                    <h3><i class="fas fa-ticket-alt"></i> ${ticket.title || 'No title'}</h3>
                    <p>${ticket.description ? (ticket.description.length > 100 ? ticket.description.substring(0, 100) + '...' : ticket.description) : ''}</p>
                    <div class="ticket-meta">
                        <span class="status-badge status-${(ticket.status || '').toLowerCase().replace(' ', '-')}">${ticket.status}</span>
                        <span class="priority-badge priority-${(ticket.priority || '').toLowerCase()}">${ticket.priority}</span>
                        <span><i class="fas fa-calendar"></i> ${formatDate(ticket.created_at)}</span>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => {
            console.error(err);
            container.innerHTML = '<p class="no-data">Error loading tickets</p>';
        });
}

function submitEmployeeTicket(event) {
    event.preventDefault();

    const formData = {
        ticket_type: document.getElementById('emp-ticket-type').value,
        printer_id: parseInt(document.getElementById('emp-ticket-printer').value) || null,
        device_name: document.getElementById('emp-device-name').value || null,
        affected_users_count: 1,
        title: document.getElementById('emp-ticket-title').value,
        description: document.getElementById('emp-ticket-description').value,
        priority: '',
        reporter_email: document.getElementById('emp-ticket-email').value || null
    };

    fetch('/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    })
        .then(r => r.json())
        .then(data => {
            if (data.message || data.id) {
                alert('Your support request has been submitted successfully!');
                document.getElementById('employee-ticket-form').reset();
                updateEmployeeTicketType();
                switchPortalTab('my-tickets');
            } else {
                alert('Error submitting request');
            }
        })
        .catch(err => {
            console.error(err);
            alert('Error submitting request');
        });
}

document.addEventListener('DOMContentLoaded', function () {
    if (typeof initTheme === 'function') initTheme();
    loadEmployeePrinters();
    updateEmployeeTicketType();
});
