// Main JavaScript functionality for the Network Configuration Generator

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. Tooltips do Bootstrap ---
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // --- 2. Auto-fechamento de alertas de sucesso ---
    const alerts = document.querySelectorAll('.alert-success');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // --- 3. Validação nativa de formulários do Bootstrap ---
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // --- 4. Helpers de Validação (Escopo Global) ---
    window.validateIP = function(ip) {
        const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipRegex.test(ip);
    };

    window.validateVLAN = function(vlanId) {
        const val = vlanId.toLowerCase().trim();
        if (val === 'all') return true;
        // Permite números, hífens para ranges e vírgulas para listas
        if (val.includes('-') || val.includes(',')) {
            return /^[\d\s\-,]+$/.test(val);
        }
        const vlan = parseInt(val);
        return !isNaN(vlan) && vlan >= 1 && vlan <= 4094;
    };

    // --- 5. Validação em Tempo Real (IP e VLAN) ---
    const ipInputs = document.querySelectorAll('input[name="ip_address"], input[name="gateway"]');
    ipInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !validateIP(this.value)) {
                this.setCustomValidity('Invalid IP');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
            }
        });
    });

    const vlanInputs = document.querySelectorAll('input[name="vlan_id"], input[name="access_vlan"], input[name="voice_vlan"], input[name="allowed_vlans"]');
    vlanInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !validateVLAN(this.value)) {
                this.setCustomValidity('Invalid VLAN format');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
            }
        });
    });

    // --- 6. Confirmação de Exclusão ---
    document.querySelectorAll('a[href*="/delete_"]').forEach(link => {
        link.addEventListener('click', function(event) {
            if (!confirm('Are you sure? This action cannot be undone.')) {
                event.preventDefault();
            }
        });
    });

    // --- 7. Lógica de Interface (Access/Trunk/AOS-CX) ---
    const modeSelect = document.getElementById('mode');
    const isAosCxCheckbox = document.getElementById('is_aos_cx');
    
    if (modeSelect && isAosCxCheckbox) {
        const accessFields = document.getElementById('access_fields');
        const trunkFields = document.getElementById('trunk_fields');
        const aosCxOptions = document.getElementById('aos_cx_options');
        const aosCxRoutedFields = document.getElementById('aos_cx_routed_fields');
        const aosCxRadios = document.getElementsByName('aos_cx_type');
        const modeContainer = document.getElementById('mode_container');

        function toggleModeFields() {
            const isAosCx = isAosCxCheckbox.checked;
            const aosCxType = Array.from(aosCxRadios).find(r => r.checked)?.value || 'non-routed';
            const mode = modeSelect.value;

            // Painel AOS-CX
            if (aosCxOptions) aosCxOptions.style.display = isAosCx ? 'block' : 'none';
            
            // Campos Roteados vs Switching
            if (isAosCx && aosCxType === 'routed') {
                if (aosCxRoutedFields) aosCxRoutedFields.style.display = 'block';
                if (modeContainer) modeContainer.style.display = 'none';
                if (accessFields) accessFields.style.display = 'none';
                if (trunkFields) trunkFields.style.display = 'none';
            } else {
                if (aosCxRoutedFields) aosCxRoutedFields.style.display = 'none';
                if (modeContainer) modeContainer.style.display = 'block';
                
                // Lógica de Access/Trunk padrão
                if (accessFields) accessFields.style.display = (mode === 'access') ? 'block' : 'none';
                if (trunkFields) trunkFields.style.display = (mode === 'trunk') ? 'block' : 'none';
            }
        }

        modeSelect.addEventListener('change', toggleModeFields);
        isAosCxCheckbox.addEventListener('change', toggleModeFields);
        aosCxRadios.forEach(r => r.addEventListener('change', toggleModeFields));
        toggleModeFields(); // Estado inicial
    }

    // --- 8. Lógica de SVI (VLAN Interface) ---
    const noIpCheckbox = document.getElementById('no_ip_address');
    if (noIpCheckbox) {
        const ipAddress = document.getElementById('ip_address');
        const prefixLength = document.getElementById('prefix_length');
        
        function toggleIpFields() {
            const isDisabled = noIpCheckbox.checked;
            if (ipAddress) { ipAddress.disabled = isDisabled; if(isDisabled) ipAddress.value = ''; }
            if (prefixLength) { prefixLength.disabled = isDisabled; if(isDisabled) prefixLength.value = ''; }
        }
        noIpCheckbox.addEventListener('change', toggleIpFields);
        toggleIpFields();
    }
});

// --- Funções fora do DOMContentLoaded (Gatilhos de Botão) ---

function previewConfig(platform) {
    const modalEl = document.getElementById('configPreviewModal');
    if (!modalEl) return;

    const modal = new bootstrap.Modal(modalEl);
    const content = document.getElementById('configPreviewContent');
    content.textContent = 'Loading configuration...';
    modal.show();

    fetch(`/preview_config/${platform}`)
        .then(response => response.json())
        .then(data => {
            content.textContent = data.error ? `Error: ${data.error}` : data.config;
            content.className = data.error ? 'bg-danger text-light p-3 rounded' : 'bg-dark text-light p-3 rounded';
        })
        .catch(error => {
            content.textContent = `Error: ${error.message}`;
            content.className = 'bg-danger text-light p-3 rounded';
        });
}

function copyToClipboard(text) {
    if (!text || text.includes('Loading')) return;

    navigator.clipboard.writeText(text).then(function() {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1060'; // Garante que apareça sobre o modal
        
        container.innerHTML = `
            <div class="toast show" role="alert">
                <div class="toast-header">
                    <i class="fas fa-check-circle text-success me-2"></i>
                    <strong class="me-auto">Success</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">Configuration copied to clipboard!</div>
            </div>
        `;
        document.body.appendChild(container);
        setTimeout(() => container.remove(), 3000);
    }).catch(err => console.error('Error:', err));
}