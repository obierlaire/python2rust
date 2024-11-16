use actix_web::{web, App, HttpResponse, HttpServer};
use rayon::prelude::*;
use std::time::Instant;

// Keep the same algorithm but with parallel processing
fn calculate_primes_up_to(n: u32) -> Vec<u32> {
    (2..=n).into_par_iter()
        .filter(|&num| {
            let sqrt = (num as f64).sqrt() as u32;
            (2..=sqrt).all(|i| num % i != 0)
        })
        .collect()
}

// Keep the same algorithm but with parallel processing
fn matrix_multiply(size: usize) -> Vec<Vec<i64>> {
    let matrix1: Vec<Vec<i64>> = (0..size)
        .map(|i| (0..size).map(|j| (i + j) as i64).collect())
        .collect();
    
    let matrix2: Vec<Vec<i64>> = (0..size)
        .map(|i| (0..size).map(|j| (i * j) as i64).collect())
        .collect();
    
    (0..size).into_par_iter()
        .map(|i| {
            (0..size)
                .map(|j| {
                    (0..size)
                        .map(|k| matrix1[i][k] * matrix2[k][j])
                        .sum()
                })
                .collect()
        })
        .collect()
}

// Exactly match Python's HTML template
const HTML_TEMPLATE: &str = r#"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Demo</title>
    <style>
        body { 
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Performance Demonstration</h1>
    <form action="/" method="post">
        <button type="submit">Run Heavy Computation</button>
    </form>
    
    {results}
</body>
</html>"#;

async fn index(method: actix_web::http::Method) -> HttpResponse {
    // Create the results section only for POST requests, matching Python's {% if results %}
    let results = if method == actix_web::http::Method::POST {
        let start_time = Instant::now();
        
        // Calculate primes up to 1000000 (same as Python)
        let primes = calculate_primes_up_to(1000000);
        
        // Perform 200x200 matrix multiplication (same as Python)
        let matrix_result = matrix_multiply(200);
        let matrix_sum: i64 = matrix_result.iter()
            .flat_map(|row| row.iter())
            .sum();
        
        let elapsed = start_time.elapsed().as_secs_f64();
        
        // Format results exactly like Python's template
        format!(r#"
    <h2>Results:</h2>
    <p>Time taken: {:.2} seconds</p>
    <h3>Statistics:</h3>
    <ul>
        <li>Number of primes found: {}</li>
        <li>Last few primes: {}</li>
        <li>Matrix multiplication sum: {}</li>
    </ul>"#,
            elapsed,
            primes.len(),
            format!("{:?}", &primes[primes.len()-5..]),  // Format array the same as Python str()
            matrix_sum
        )
    } else {
        String::new()  // Empty string for GET requests, matching Python's {% if results %}
    };

    // Replace the results placeholder in the template
    let html = HTML_TEMPLATE.replace("{results}", &results);

    HttpResponse::Ok()
        .content_type("text/html; charset=utf-8")
        .body(html)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("Server starting at http://127.0.0.1:8080");
    
    HttpServer::new(|| {
        App::new()
            .route("/", web::get().to(index))
            .route("/", web::post().to(index))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}