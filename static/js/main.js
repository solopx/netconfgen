// Main JavaScript functionality for the Network Configuration Generator

document.addEventListener('DOMContentLoaded', function() {
    
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    const alerts = document.querySelectorAll('.alert-success');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

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

    window.validateIP = function(ip) {
        const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipRegex.test(ip);
    };

    window.validateVLAN = function(vlanId) {
        const val = vlanId.toLowerCase().trim();
        if (val === 'all') return true;
        if (val.includes('-') || val.includes(',')) {
            return /^[\d\s\-,]+$/.test(val);
        }
        const vlan = parseInt(val);
        return !isNaN(vlan) && vlan >= 1 && vlan <= 4094;
    };

    window.validateHostname = function(h) {
        if (validateIP(h)) return true;
        if (!h || h.length > 253) return false;
        return h.split('.').every(label =>
            label.length > 0 && label.length <= 63 &&
            !label.startsWith('-') && !label.endsWith('-') &&
            /^[a-zA-Z0-9-]+$/.test(label)
        );
    };

    const ipInputs = document.querySelectorAll('input[name="ip_address"], input[name="gateway"], input[name="network"]');
    ipInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !validateIP(this.value)) {
                this.setCustomValidity('Invalid IP address');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
            }
        });
    });

    const hostnameInputs = document.querySelectorAll('input[name="ntp_server"], input[name="syslog_server"]');
    hostnameInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !validateHostname(this.value)) {
                this.setCustomValidity('Invalid address');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
            }
        });
    });

    const dnsInput = document.querySelector('input[name="dns_server"]');
    if (dnsInput) {
        dnsInput.addEventListener('blur', function() {
            if (this.value && !validateIP(this.value)) {
                this.setCustomValidity('Invalid IP address');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
            }
        });
    }

    const snmpInput = document.querySelector('input[name="snmp_community"]');
    if (snmpInput) {
        snmpInput.addEventListener('blur', function() {
            const invalid = this.value && /[\s"']/.test(this.value);
            if (invalid) {
                this.setCustomValidity('Must not contain spaces or quotes');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
            }
        });
    }

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

    const modeSelect = document.getElementById('mode');
    const isAosCxCheckbox = document.getElementById('is_aos_cx');
    
    if (modeSelect && isAosCxCheckbox) {
        const accessFields = document.getElementById('access_fields');
        const trunkFields = document.getElementById('trunk_fields');
        const aosCxOptions = document.getElementById('aos_cx_options');
        const aosCxRoutedFields = document.getElementById('aos_cx_routed_fields');
        const aosCxRadios = document.getElementsByName('aos_cx_type');
        const modeContainer = document.getElementById('mode_container');

        const ipAddressInput = document.getElementById('ip_address');
        const prefixLengthInput = document.getElementById('prefix_length');
        const ipRequiredStar = document.getElementById('ip_required_star');
        const prefixRequiredStar = document.getElementById('prefix_required_star');

        function toggleModeFields() {
            const isAosCx = isAosCxCheckbox.checked;
            const aosCxType = Array.from(aosCxRadios).find(r => r.checked)?.value || 'non-routed';
            const mode = modeSelect.value;
            const isRoutedAosCx = isAosCx && aosCxType === 'routed';

            if (aosCxOptions) aosCxOptions.style.display = isAosCx ? 'block' : 'none';

            if (isRoutedAosCx) {
                if (aosCxRoutedFields) aosCxRoutedFields.style.display = 'block';
                if (modeContainer) modeContainer.style.display = 'none';
                if (accessFields) accessFields.style.display = 'none';
                if (trunkFields) trunkFields.style.display = 'none';
                if (ipAddressInput) ipAddressInput.required = true;
                if (prefixLengthInput) prefixLengthInput.required = true;
                if (ipRequiredStar) ipRequiredStar.style.display = '';
                if (prefixRequiredStar) prefixRequiredStar.style.display = '';
            } else {
                if (aosCxRoutedFields) aosCxRoutedFields.style.display = 'none';
                if (modeContainer) modeContainer.style.display = 'block';
                if (accessFields) accessFields.style.display = (mode === 'access') ? 'block' : 'none';
                if (trunkFields) trunkFields.style.display = (mode === 'trunk') ? 'block' : 'none';
                if (ipAddressInput) { ipAddressInput.required = false; ipAddressInput.setCustomValidity(''); ipAddressInput.classList.remove('is-invalid'); }
                if (prefixLengthInput) { prefixLengthInput.required = false; prefixLengthInput.setCustomValidity(''); prefixLengthInput.classList.remove('is-invalid'); }
                if (ipRequiredStar) ipRequiredStar.style.display = 'none';
                if (prefixRequiredStar) prefixRequiredStar.style.display = 'none';
            }
        }

        modeSelect.addEventListener('change', toggleModeFields);
        isAosCxCheckbox.addEventListener('change', toggleModeFields);
        aosCxRadios.forEach(r => r.addEventListener('change', toggleModeFields));
        toggleModeFields();
    }

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

function addAclEntry() {
    const template = document.getElementById('entry-row-template');
    if (!template) return;
    const tbody = document.getElementById('entries-body');
    const idx = tbody.querySelectorAll('tr').length;
    const clone = template.content.cloneNode(true);
    clone.querySelectorAll('[name]').forEach(el => {
        el.name = el.name.replace('__IDX__', idx);
    });
    tbody.appendChild(clone);
    applyAclTypeVisibility();
}

function removeAclEntry(btn) {
    const row = btn.closest('tr');
    const tbody = document.getElementById('entries-body');
    row.remove();
    tbody.querySelectorAll('tr').forEach((tr, newIdx) => {
        tr.querySelectorAll('[name]').forEach(el => {
            el.name = el.name.replace(/_\d+$/, '_' + newIdx);
        });
    });
}

function toggleSrcFields(sel) {
    const row = sel.closest('tr');
    const srcInput = row.querySelector('.src-ip');
    const prefixInput = row.querySelector('.src-prefix');
    if (!srcInput || !prefixInput) return;
    if (sel.value === 'any') {
        srcInput.disabled = true; srcInput.value = '';
        prefixInput.disabled = true; prefixInput.value = '';
    } else if (sel.value === 'host') {
        srcInput.disabled = false;
        prefixInput.disabled = true; prefixInput.value = '';
    } else {
        srcInput.disabled = false;
        prefixInput.disabled = false;
    }
}

function toggleDstFields(sel) {
    const row = sel.closest('tr');
    const dstInput = row.querySelector('.dst-ip');
    const prefixInput = row.querySelector('.dst-prefix');
    if (!dstInput || !prefixInput) return;
    if (sel.value === 'any') {
        dstInput.disabled = true; dstInput.value = '';
        prefixInput.disabled = true; prefixInput.value = '';
    } else if (sel.value === 'host') {
        dstInput.disabled = false;
        prefixInput.disabled = true; prefixInput.value = '';
    } else {
        dstInput.disabled = false;
        prefixInput.disabled = false;
    }
}

function applyAclTypeVisibility() {
    const typeSelect = document.getElementById('acl_type');
    if (!typeSelect) return;
    const isExtended = typeSelect.value === 'extended';
    document.querySelectorAll('.acl-extended-col').forEach(el => {
        el.style.display = isExtended ? '' : 'none';
    });
}

function toggleAclType() {
    applyAclTypeVisibility();
}

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
        container.style.zIndex = '1060';
        
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