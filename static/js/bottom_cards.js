var player_id
var displaying_results = false

socket.on('results', (r)=>{
    console.log(r)
    displaying_results = true

    table_clear()

    const played_card = r["played_card"]
    const category = r["played_category"]
    const to_beat = played_card["attributes"][category]
    const challenge_cards = r["challenge_cards"]


    var player_row = ["Player", "Played card"]
    var title_row = ["Title", played_card["title"]]
    var category_row = (["Category", category])
    var score_row = ["Score", to_beat]

    for (const challenger in r["challenge_cards"]) {
        player_row.push(challenger)
        title_row.push(challenge_cards[challenger]["title"])
        category_row.push(category)
        score_row.push(challenge_cards[challenger]["attributes"][category])
    }

    table_add_row(player_row)
    table_add_row(title_row)
    table_add_row(category_row)
    let score_row_elements = Array.from(table_add_row(score_row).childNodes)

    score_row_elements.slice(2).forEach((cell)=>{
        if (cell.innerHTML < to_beat)
            cell.className = "cell_fail"
        else
            cell.className = "cell_survive"
    })

    console.log(score_row_elements)

    setTimeout(()=>{
        displaying_results = false
        get_state()
    }, 4000)
})

key_handle_json = {
    "turn_uid": handle_turn_id,
    "player_uid": (uid)=>{player_id=uid},
    "turn_name": (name)=>(set_id_text("player_name", name)),
    "active_card": handle_active_card,
    "player_scores": handle_player_scores,
    "game_started": handle_game_started,
}

function handle_active_card (active_card) {
    if (!displaying_results) {
        table_clear()
        table_add_row([active_card["title"]])

        const attributes = active_card["attributes"]

        for (const category in attributes) {
            table_add_row(
                [category, attributes[category]],
                category_select.bind(undefined, category)
            )
        }
    }
}

function category_select(a) {
    socket.emit("game_action","selected_category",a)
}

function handle_turn_id (id) {
    if (player_id == id) {
        const player_name = $("#player_name")
        player_name.text(player_name.text() + " (You)")
    }
}

function handle_player_scores (scores) {
    let score_array = []
    for (const key in scores) {
        score_array.push(key + ": " + scores[key])
    }
    let text = score_array.join(",\t")
    set_id_text("scores", text)
}

$(()=>{$("#btn_start").hide()})

function handle_game_started(b) {
    if (b)
        $("#btn_start").hide()
    else
        $("#btn_start").show()
}

function set_id_text(id,text) {
    $("#" + id).text(text)
}

function createElement_as_child_of (type, parent) {
    const new_element = document.createElement(type)
    parent.appendChild(new_element)
    return new_element
}

const table = document.getElementById("display_table")

function table_add_row(row_text, click_func = undefined) { // Adds an array of strings to the table row
    const row = createElement_as_child_of("tr", table)

    row_text.forEach((text)=>{
        const cell = createElement_as_child_of("th", row)
        cell.textContent = text
        if (click_func != undefined)
            cell.onclick = click_func.bind(undefined,text)
    })

    return row
}

function table_clear() {
    table.innerHTML = ""
}

get_state()