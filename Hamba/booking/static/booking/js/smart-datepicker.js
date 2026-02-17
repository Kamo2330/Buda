/**
 * Smart Date Picker - calendar dropdown + editable input for date fields
 */
(function() {
    'use strict';

    function init() {
        var inputs = document.querySelectorAll('input[type="date"].smart-datepicker, input.smart-datepicker[type="date"]');
        inputs.forEach(function(input) {
            if (input.dataset.smartDatepicker) return;
            input.dataset.smartDatepicker = '1';

            var wrapper = document.createElement('div');
            wrapper.className = 'smart-datepicker-wrapper';
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);

            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'calendar-toggle-btn';
            btn.innerHTML = '📅';
            btn.setAttribute('aria-label', 'Open calendar');
            wrapper.appendChild(btn);

            var cal = document.createElement('div');
            cal.className = 'smart-datepicker-calendar';
            cal.style.display = 'none';
            wrapper.appendChild(cal);

            function render() {
                var y = parseInt(input.dataset.calYear || new Date().getFullYear(), 10);
                var m = parseInt(input.dataset.calMonth || new Date().getMonth(), 10);
                var first = new Date(y, m, 1);
                var last = new Date(y, m + 1, 0);
                var startDay = first.getDay();
                var days = last.getDate();
                var min = input.min ? new Date(input.min) : null;
                var max = input.max ? new Date(input.max) : null;

                cal.innerHTML = '';
                var header = document.createElement('div');
                header.className = 'calendar-header';
                var prev = document.createElement('button');
                prev.type = 'button';
                prev.className = 'calendar-nav-btn';
                prev.innerHTML = '‹';
                prev.setAttribute('aria-label', 'Previous month');
                prev.addEventListener('click', function() {
                    if (m === 0) { m = 11; y--; } else m--;
                    input.dataset.calMonth = m;
                    input.dataset.calYear = y;
                    render();
                });
                var monthYear = document.createElement('div');
                monthYear.className = 'calendar-month-year';
                monthYear.textContent = first.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                var next = document.createElement('button');
                next.type = 'button';
                next.className = 'calendar-nav-btn';
                next.innerHTML = '›';
                next.setAttribute('aria-label', 'Next month');
                next.addEventListener('click', function() {
                    if (m === 11) { m = 0; y++; } else m++;
                    input.dataset.calMonth = m;
                    input.dataset.calYear = y;
                    render();
                });
                header.appendChild(prev);
                header.appendChild(monthYear);
                header.appendChild(next);
                cal.appendChild(header);

                var weekdays = document.createElement('div');
                weekdays.className = 'calendar-weekdays';
                'Sun Mon Tue Wed Thu Fri Sat'.split(' ').forEach(function(d) {
                    var el = document.createElement('div');
                    el.className = 'calendar-weekday';
                    el.textContent = d;
                    weekdays.appendChild(el);
                });
                cal.appendChild(weekdays);

                var grid = document.createElement('div');
                grid.className = 'calendar-days';
                for (var i = 0; i < startDay; i++) {
                    var empty = document.createElement('div');
                    empty.className = 'calendar-day empty';
                    grid.appendChild(empty);
                }
                var today = new Date();
                for (var d = 1; d <= days; d++) {
                    var cell = document.createElement('button');
                    cell.type = 'button';
                    cell.className = 'calendar-day';
                    cell.textContent = d;
                    var dt = new Date(y, m, d);
                    var dateStr = y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
                    if ((min && dt < min) || (max && dt > max)) {
                        cell.classList.add('disabled');
                        cell.disabled = true;
                    } else {
                        cell.addEventListener('click', function() {
                            input.value = this.dataset.date;
                            cal.style.display = 'none';
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        });
                        cell.dataset.date = dateStr;
                    }
                    if (dt.toDateString() === today.toDateString()) cell.classList.add('today');
                    if (input.value === dateStr) cell.classList.add('selected');
                    grid.appendChild(cell);
                }
                cal.appendChild(grid);
            }

            btn.addEventListener('click', function(e) {
                e.preventDefault();
                if (input.value) {
                    var parts = input.value.split('-');
                    if (parts.length === 3) {
                        input.dataset.calYear = parts[0];
                        input.dataset.calMonth = String(parseInt(parts[1], 10) - 1);
                    }
                }
                render();
                cal.style.display = cal.style.display === 'none' ? 'block' : 'none';
            });

            input.addEventListener('focus', function() {
                render();
                cal.style.display = 'block';
            });

            document.addEventListener('click', function(e) {
                if (!wrapper.contains(e.target)) cal.style.display = 'none';
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
