document.addEventListener('DOMContentLoaded', () => {
    document.getElementById("download-btn").addEventListener("click", function() {
    const element = document.getElementById("content-to-download");
    const opt = {
        margin: 1,
        filename: 'quiz_results_review.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(element).save();
});
});