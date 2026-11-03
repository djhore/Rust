document.addEventListener("DOMContentLoaded", function () {
    const statusElement = document.getElementById("status-data");
    const categoryElement = document.getElementById("category-data");
    const statusCanvas = document.getElementById("statusChart");
    const categoryCanvas = document.getElementById("categoryChart");

    // Stop safely if this page doesn't contain the report charts.
    if (
        !statusElement ||
        !categoryElement ||
        !statusCanvas ||
        !categoryCanvas
    ) {
        return;
    }

    // Stop if Chart.js did not load.
    if (typeof Chart === "undefined") {
        console.error("Chart.js could not be loaded.");
        return;
    }

    const statusData = JSON.parse(statusElement.textContent);
    const categoryData = JSON.parse(categoryElement.textContent);

    new Chart(statusCanvas, {
        type: "bar",
        data: {
            labels: statusData.map(item => item.status),
            datasets: [{
                label: "Maintenance Requests",
                data: statusData.map(item => item.total),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });

    new Chart(categoryCanvas, {
        type: "doughnut",
        data: {
            labels: categoryData.map(item => item.category),
            datasets: [{
                label: "Requests",
                data: categoryData.map(item => item.total),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
});