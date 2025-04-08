// Utility function to generate random colors
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// Attendance Chart Function
function createAttendanceChart(canvasId, labels, presentData, absentData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    const attendanceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Present',
                    data: presentData,
                    backgroundColor: '#4e73df',
                    borderColor: '#4e73df',
                    borderWidth: 1
                },
                {
                    label: 'Absent',
                    data: absentData,
                    backgroundColor: '#e74a3b',
                    borderColor: '#e74a3b',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    beginAtZero: true
                }
            }
        }
    });
    
    return attendanceChart;
}

// Subject Attendance Pie Chart
function createSubjectPieChart(canvasId, subjects, percentages) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Generate colors for each subject
    const colors = [];
    for (let i = 0; i < subjects.length; i++) {
        colors.push(getRandomColor());
    }
    
    const subjectChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: subjects,
            datasets: [{
                data: percentages,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
    
    return subjectChart;
}

// GPA Line Chart
function createGPAChart(canvasId, semesters, gpaData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    const gpaChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: semesters,
            datasets: [{
                label: 'GPA',
                data: gpaData,
                backgroundColor: 'rgba(78, 115, 223, 0.2)',
                borderColor: '#4e73df',
                borderWidth: 2,
                pointBackgroundColor: '#4e73df',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: false,
                    min: 0,
                    max: 10,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
    
    return gpaChart;
}

// Marks Comparison Chart
function createMarksComparisonChart(canvasId, subjects, quizData, midtermData, finalData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    const marksChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: subjects,
            datasets: [
                {
                    label: 'Quiz',
                    data: quizData,
                    backgroundColor: '#4e73df',
                    borderColor: '#4e73df',
                    borderWidth: 1
                },
                {
                    label: 'Midterm',
                    data: midtermData,
                    backgroundColor: '#1cc88a',
                    borderColor: '#1cc88a',
                    borderWidth: 1
                },
                {
                    label: 'Final',
                    data: finalData,
                    backgroundColor: '#f6c23e',
                    borderColor: '#f6c23e',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
    
    return marksChart;
}
