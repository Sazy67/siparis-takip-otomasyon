document.addEventListener('DOMContentLoaded', function () {
    initToggleStatusButtons();
    initEditableCells();
});

function initToggleStatusButtons() {
    document.querySelectorAll('.toggle-status-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var orderId = btn.dataset.orderId;
            var itemId = btn.dataset.itemId;
            btn.disabled = true;

            fetch('/order/' + orderId + '/item/' + itemId + '/toggle-status', {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(function (res) {
                    if (!res.ok) throw new Error('Durum guncellenemedi');
                    return res.json();
                })
                .then(function (data) {
                    btn.textContent = data.status;
                    if (data.status === 'Uretildi') {
                        btn.classList.remove('btn-outline-secondary');
                        btn.classList.add('btn-success');
                    } else {
                        btn.classList.remove('btn-success');
                        btn.classList.add('btn-outline-secondary');
                    }
                })
                .catch(function () {
                    alert('Durum guncellenirken hata olustu.');
                })
                .finally(function () {
                    btn.disabled = false;
                });
        });
    });
}

function initEditableCells() {
    document.querySelectorAll('.editable-cell').forEach(function (cell) {
        cell.addEventListener('click', function () {
            if (cell.querySelector('input')) return; // zaten duzenleniyor

            var span = cell.querySelector('.display-value');
            var currentValue = span.textContent.trim();

            var input = document.createElement('input');
            input.type = 'number';
            input.step = '0.01';
            input.min = '0';
            input.className = 'form-control form-control-sm';
            input.value = currentValue;

            cell.innerHTML = '';
            cell.appendChild(input);
            input.focus();
            input.select();

            function commit() {
                var newValue = input.value;
                submitItemUpdate(cell, newValue);
            }

            input.addEventListener('blur', commit);
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    input.blur();
                } else if (e.key === 'Escape') {
                    cell.innerHTML = '<span class="display-value">' + currentValue + '</span>';
                }
            });
        });
    });
}

function submitItemUpdate(cell, newValue) {
    var row = cell.closest('tr');
    var itemId = cell.dataset.itemId;
    var field = cell.dataset.field;

    var quantityCell = row.querySelector('.editable-cell[data-field="quantity"]');
    var priceCell = row.querySelector('.editable-cell[data-field="unit_price"]');

    var quantity = field === 'quantity' ? newValue : getCellValue(quantityCell);
    var unitPrice = field === 'unit_price' ? newValue : getCellValue(priceCell);

    var orderIdMatch = window.location.pathname.match(/\/order\/(\d+)/);
    var orderIdValue = orderIdMatch ? orderIdMatch[1] : null;

    fetch('/order/' + orderIdValue + '/item/' + itemId + '/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'quantity=' + encodeURIComponent(quantity) + '&unit_price=' + encodeURIComponent(unitPrice)
    })
        .then(function (res) {
            return res.json().then(function (data) {
                if (!res.ok) throw new Error(data.error || 'Guncellenemedi');
                return data;
            });
        })
        .then(function (data) {
            quantityCell.innerHTML = '<span class="display-value">' + data.quantity + '</span>';
            priceCell.innerHTML = '<span class="display-value">' + data.unit_price.toFixed(2) + '</span>';
            row.querySelector('.item-total-price').textContent = data.total_price.toFixed(2);

            var vadeliUnitCell = row.querySelector('.item-vadeli-unit-price');
            var vadeliTotalCell = row.querySelector('.item-vadeli-total-price');
            if (vadeliUnitCell && data.vadeli_unit_price !== null) {
                vadeliUnitCell.textContent = data.vadeli_unit_price.toFixed(2);
            }
            if (vadeliTotalCell && data.vadeli_total_price !== null) {
                vadeliTotalCell.textContent = data.vadeli_total_price.toFixed(2);
            }

            var orderTotalEl = document.getElementById('order-total-amount');
            if (orderTotalEl) {
                orderTotalEl.textContent = data.order_total_amount.toFixed(2) + ' TL';
            }
        })
        .catch(function (err) {
            alert(err.message || 'Guncellenirken hata olustu.');
            location.reload();
        });
}

function getCellValue(cell) {
    var span = cell.querySelector('.display-value');
    return span ? span.textContent.trim() : cell.textContent.trim();
}
