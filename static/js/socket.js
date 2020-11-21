var socket = io()

socket.on('redirect',(url) => {
    onbeforeunload = () => {}
    document.location.href = url
})
