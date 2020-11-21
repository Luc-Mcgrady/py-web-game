function send_choices(choices) {
    socket.emit("game_action","boxes",choices)
}
function get_state() {
    socket.emit("game_state")
}


socket.on('game_state_receive',(m) => {
    console.log(m)
})
socket.on('game_over',(name) => {
    get_state()
    console.log(name + " Wins!")
})
socket.on('game_turn',(name) => {
    console.log(name + "'s turn")
    get_state()
})


get_state()