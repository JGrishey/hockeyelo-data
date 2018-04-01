//
//  Jacob Grishey
//  Hockey Elo Simulation
//  Rust
//

use std::fs::File;

extern crate reqwest;

fn main() {
    let text = reqwest::get("https://statsapi.web.nhl.com/api/v1/schedule?startDate=2017-10-04&endDate=2018-04-07&expand=schedule.linescore&site=en_nhl")
        .text();

    println!("{}", text);
}

struct Season {
    teams: Vec<Team>
}

struct Team {
    name: String,
    division: String,
    wins: u32,
    losses: u32,
    overtime_losses: u32,
    row: u32,
    elo: u32,
    playoffs: u32,
    d1: u32,
    conf: u32,
    pres: u32,
    r2: u32,
    r3: u32,
    r4: u32,
    cup: u32,
}
