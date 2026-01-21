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
        setupContextMenuHandlers();
        setupMenuActions();
        setupKeyboardShortcuts();
    }

    function setupZoomControls() {
        const zoomBtns = $('.zoom-btn');
        const zoomLevel = $('.zoom-level');

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
        const cells = $('.batch-card');

        cells.each(function() {
            const $cell = $(this);
            const batchCode = $cell.find('.batch-code').text().toLowerCase();
            const productName = $cell.find('.batch-product').text().toLowerCase();
            const qtyText = $cell.find('.batch-qty').text().toLowerCase();

            if (query === '') {
                $cell.removeClass('search-hidden search-highlight');
            } else if (batchCode.includes(query) || productName.includes(query) || qtyText.includes(query)) {
                $cell.removeClass('search-hidden').addClass('search-highlight');
            } else {
                $cell.addClass('search-hidden').removeClass('search-highlight');
            }
        });
    }

    function setupCellClickHandlers() {
        $(document).on('click', '.batch-card.occupied', function(e) {
            // Don't trigger on menu button click
            if ($(e.target).closest('.card-menu-trigger').length) {
                return;
            }
            // Open batch details
            const batchId = $(this).data('batch-id');
            if (batchId) {
                openBatchDetails(batchId);
            }
        });

        // Empty cell click
        $(document).on('click', '.batch-card.empty', function(e) {
            // Open add batch dialog
            const gridId = $(this).data('grid-id');
            if (gridId) {
                openAddBatchDialog(gridId);
            }
        });
    }

    function setupContextMenuHandlers() {
        $(document).on('click', '.card-menu-trigger', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const $card = $(this).closest('.batch-card');
            const menuX = e.pageX;
            const menuY = e.pageY;
            
            showContextMenu(menuX, menuY, $card);
        });

        // Close menu on click outside
        $(document).on('click', function(e) {
            if (!$(e.target).closest('.batch-context-menu, .card-menu-trigger').length) {
                hideContextMenu();
            }
        });

        // Close menu with Escape
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape') {
                hideContextMenu();
            }
        });
    }

    function showContextMenu(x, y, $card) {
        const $menu = $('.batch-context-menu');
        
        // Adjust position if menu goes off screen
        const menuWidth = 220;
        const menuHeight = 280;
        
        if (x + menuWidth > $(window).width()) {
            x = $(window).width() - menuWidth - 10;
        }
        if (y + menuHeight > $(window).height()) {
            y = $(window).height() - menuHeight - 10;
        }
        
        $menu.css({
            left: x + 'px',
            top: y + 'px'
        }).addClass('show').data('card', $card);
    }

    function hideContextMenu() {
        $('.batch-context-menu').removeClass('show').removeData('card');
    }

    function setupMenuActions() {
        $(document).on('click', '.menu-item', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const action = $(this).data('action');
            const $menu = $('.batch-context-menu');
            const $card = $menu.data('card');

            if ($card) {
                const batchId = $card.data('batch-id');
                const gridId = $card.data('grid-id');

                switch(action) {
                    case 'pick':
                        openPickDialog(batchId);
                        break;
                    case 'move':
                        openMoveDialog(gridId, batchId);
                        break;
                    case 'transfer':
                        openTransferDialog(batchId);
                        break;
                    case 'details':
                        openBatchDetails(batchId);
                        break;
                    case 'location':
                        openLocationDetails(gridId);
                        break;
                    case 'remove':
                        confirmRemove(gridId, batchId);
                        break;
                }
            }

            hideContextMenu();
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
                hideContextMenu();
                $('.search-input').val('').trigger('input');
            }
        });
    }

    // Action handlers
    function openPickDialog(batchId) {
        console.log('Open pick dialog for batch:', batchId);
        // TODO: Create pick wizard dialog
    }

    function openMoveDialog(gridId, batchId) {
        console.log('Open move dialog for batch:', batchId, 'grid:', gridId);
        // TODO: Create move location dialog
    }

    function openTransferDialog(batchId) {
        console.log('Open transfer dialog for batch:', batchId);
        // TODO: Create transfer warehouse dialog
    }

    function openBatchDetails(batchId) {
        console.log('Open batch details:', batchId);
        // TODO: Create batch details view
    }

    function openLocationDetails(gridId) {
        console.log('Open location details:', gridId);
        // TODO: Create location details dialog
    }

    function openAddBatchDialog(gridId) {
        console.log('Open add batch dialog for grid:', gridId);
        // TODO: Create add batch dialog
    }

    function confirmRemove(gridId, batchId) {
        console.log('Remove batch:', batchId, 'from grid:', gridId);
        // TODO: Create confirmation dialog and remove
    }

});
