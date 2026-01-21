odoo.define('hdi_wms.warehouse_layout_grid', function(require) {
    'use strict';
    const core = require('web.core');
    const $ = require('jquery');

    let currentZoom = 100;

    $(document).ready(function() {
        initWarehouseGrid();
    });

    function initWarehouseGrid() {
        setupZoomControls();
        setupSearchFilter();
        setupCellClickHandlers();
        setupKeyboardShortcuts();
    }

    function setupZoomControls() {
        const zoomBtns = $('.zoom-btn');
        const zoomLevel = $('.zoom-level');
        const gridWrapper = $('#grid-wrapper');

        zoomBtns.on('click', function() {
            const action = $(this).data('zoom');
            
            if (action === 'plus' && currentZoom < 200) {
                currentZoom += 10;
            } else if (action === 'minus' && currentZoom > 50) {
                currentZoom -= 10;
            }

            updateZoom();
            zoomLevel.text(currentZoom + '%');
        });
    }

    function updateZoom() {
        const grid = $('.warehouse-grid');
        const scale = currentZoom / 100;
        grid.css('transform', `scale(${scale})`);
        grid.css('transform-origin', 'top left');
    }

    function setupSearchFilter() {
        const searchInput = $('.search-input');
        let searchTimeout;

        searchInput.on('input', function() {
            clearTimeout(searchTimeout);
            const query = $(this).val().toLowerCase().trim();

            searchTimeout = setTimeout(function() {
                filterCells(query);
            }, 300);
        });
    }

    function filterCells(query) {
        const cells = $('.grid-cell');

        cells.each(function() {
            const $cell = $(this);
            const lot = $cell.find('.quant-lot').text().toLowerCase();
            const product = $cell.find('.quant-product').text().toLowerCase();

            if (query === '') {
                $cell.removeClass('search-hidden search-highlight');
            } else if (lot.includes(query) || product.includes(query)) {
                $cell.removeClass('search-hidden').addClass('search-highlight');
            } else {
                $cell.addClass('search-hidden').removeClass('search-highlight');
            }
        });
    }

    function setupCellClickHandlers() {
        $(document).on('click', '.grid-cell.empty', function() {
            const locId = $(this).data('location-id');
            console.log('Empty cell clicked. Location ID:', locId);
            // TODO: Open assign wizard
        });

        $(document).on('click', '.grid-cell.occupied', function(e) {
            if (!$(e.target).closest('.cell-action-btn').length) {
                const batchId = $(this).find('.quant-cell').data('batch-id');
                console.log('Cell clicked. Batch ID:', batchId);
            }
        });

        $(document).on('click', '.cell-action-btn.edit', function(e) {
            e.stopPropagation();
            const batchId = $(this).closest('.quant-cell').data('batch-id');
            console.log('Edit batch:', batchId);
            // TODO: Open edit dialog
        });

        $(document).on('click', '.cell-action-btn.move', function(e) {
            e.stopPropagation();
            const batchId = $(this).closest('.quant-cell').data('batch-id');
            console.log('Move batch:', batchId);
            // TODO: Open move dialog
        });

        $(document).on('click', '.cell-action-btn.remove', function(e) {
            e.stopPropagation();
            const batchId = $(this).closest('.quant-cell').data('batch-id');
            console.log('Remove batch:', batchId);
            // TODO: Open confirm dialog
        });
    }

    function setupKeyboardShortcuts() {
        $(document).on('keydown', function(e) {
            const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
            const ctrlKey = isMac ? e.metaKey : e.ctrlKey;

            if (ctrlKey && e.which === 70) { // Ctrl/Cmd+F
                e.preventDefault();
                $('.search-input').focus().select();
            } else if (ctrlKey && e.which === 187) { // Ctrl/Cmd++
                e.preventDefault();
                $('.zoom-btn[data-zoom="plus"]').click();
            } else if (ctrlKey && e.which === 189) { // Ctrl/Cmd+−
                e.preventDefault();
                $('.zoom-btn[data-zoom="minus"]').click();
            } else if (e.which === 27) { // Esc
                $('.search-input').val('').trigger('input');
            }
        });
    }

});
