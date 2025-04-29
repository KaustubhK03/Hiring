document.addEventListener("DOMContentLoaded", function () {
    var ctx = document.getElementById("resultChart").getContext("2d");
    new Chart(ctx, {
        type: "pie",
        data: {
            labels: graphData.labels,
            datasets: [{
                data: graphData.data,
                backgroundColor: ["#28a745", "#dc3545"]
            }]
        },
        options: {
            responsive: false, // Prevent automatic resizing
            maintainAspectRatio: false, // Allow custom size
            width: 200, // Set desired width
            height: 200 // Set desired height
        }
    });
    // Bar Chart (Top Scores)
    var ctx2 = document.getElementById("topScoresChart").getContext("2d");
    new Chart(ctx2, {
        type: "bar",
        data: {
            labels: topScoresData.labels,
            datasets: [{
                label: "Marks",
                data: topScoresData.data,
                backgroundColor: topScoresData.colors
            }]
        }
    });
});