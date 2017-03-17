(function($) {
    $.QueryString = (function(a) {
        if (a === "") return {};
        var b = {};
        for (var i = 0; i < a.length; ++i)
        {
            var p=a[i].split('=', 2);
            if (p.length != 2) continue;
            b[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
        }
        return b;
    })(window.location.search.substr(1).split('&'));
})(jQuery);

$(document).ready(function() {
    var userId = $.QueryString.id,
        username, matchId,
        lobbySource, userMatchesSource, roundsSource;

    function showRegistrationModal() {
        $(".modal.register")
            .modal({
                closable: false,
                onApprove : function() {
                    $(".modal.register .actions .positive").addClass("loading");
                    $.ajax({
                        url: "/register/",
                        data: JSON.stringify({
                            username: $(".register [name=username]").val(),
                            strategy: $(".register [name=strategy]").val()
                        }),
                        contentType: "application/json",
                        type: "POST",
                        success: function(resp) {
                            window.location = "/?id=" + encodeURIComponent(resp.id);
                        }
                    });
                    return false;
                }
            }).modal("show");
    }

    function leaveLobby(async) {
        return $.ajax({
            url: "/leave/",
            data: JSON.stringify({id: userId}),
            contentType: "application/json",
            type: "POST",
            async: (async === undefined || async)
        });
    }

    function enterLobby() {
        return $.ajax({
            url: "/enter/",
            data: JSON.stringify({id: userId}),
            contentType: "application/json",
            type: "POST",
            success: function(resp) {
                username = resp.username;
                $(window).on("unload", function() {
                    leaveLobby(false);
                });
            }
        });
    }

    function makePlayerListItem(player) {
        var item = $("<div class='item player'></div>");
        item.append($("<i class='user middle aligned icon'></i>"));
        var a = $("<a class='header'></a>");
        a.text(player.username);
        a.attr("id", "player-" + player.id);
        var content = $("<div class='content'></div>");
        content.append(a);
        item.append(content);
        return item;
    }

    function listPlayers() {
        $(".lobby .list").empty();

        if (!lobbySource) {
            lobbySource = new EventSource("/stream?channel=lobby");
            lobbySource.addEventListener('enter', function(event) {
                var data = JSON.parse(event.data);
                $(".lobby .list").append(makePlayerListItem(data));
            }, false);
            lobbySource.addEventListener('leave', function(event) {
                var data = JSON.parse(event.data);
                $("#player-" + data.id).parents(".item").remove();
            }, false);
        }

        $(".lobby .list-container").addClass("loading");
        return $.ajax({
            url: "/lobby/",
            type: "GET",
            success: function(resp) {
                $(".lobby .list-container").removeClass("loading");
                var list = $(".lobby .list");
                for (var i=0; i < resp.players.length; i++) {
                    if (resp.players[i].id !== userId && $("#player-" + resp.players[i].id).length === 0) {
                        list.append(makePlayerListItem(resp.players[i]));
                    }
                }
            }
        });
    }

    function bindPlayerClick() {
        $(".lobby").on("click", ".player a", function() {
            var opponentId = $(this).attr("id").replace("player-", ""),
                opponentUsername = $(this).text();
            $(".lobby .list-container").addClass("loading");
            $.ajax({
                url: "/matches/",
                data: JSON.stringify({
                    proponent: {id: userId, username: username},
                    opponent: {id: opponentId, username: opponentUsername}
                }),
                contentType: "application/json",
                type: "POST",
                success: function(resp) {
                    $(".lobby .list-container").removeClass("loading");
                }
            });
        });
    }

    function makeMatchListItem(id, match) {
        var item = $("<div class='item match'></div>");
        item.append($("<i class='trophy middle aligned icon'></i>"));
        var a = $("<a class='header'></a>");
        a.text("vs. " + match.opponent.username);
        a.attr("id", "match-" + id);
        var content = $("<div class='content'></div>");
        content.append(a);
        item.append(content);
        return item;
    }

    function listMatches() {
        $(".matches .list").empty();

        if (!userMatchesSource) {
            userMatchesSource = new EventSource("/stream?channel=user:" + userId + ":matches");
            userMatchesSource.addEventListener('add', function(event) {
                var data = JSON.parse(event.data);
                $(".matches .list").append(makeMatchListItem(data.id, data));
            }, false);
        }

        $(".matches .list-container").addClass("loading");
        return $.ajax({
            url: "/matches/",
            data: {"id": userId},
            type: "GET",
            success: function(resp) {
                $(".matches .list-container").removeClass("loading");
                var list = $(".matches .list");
                $.each(resp.matches, function(matchId, match) {
                    if ($("#match-" + matchId).length === 0) {
                        list.append(makeMatchListItem(matchId, match));
                    }
                });
            }
        });
    }

    function bindMatchClick() {
        $(".matches").on("click", ".match a", function() {
            matchId = $(this).attr("id").replace("match-", "");
            $(".matches .list-container").addClass("loading");
            listRounds().then(function() {
                $(".matches .list-container").removeClass("loading");
            });
        });
    }

    function makeRoundTableRow(round) {
        var row = $("<tr class='round'></tr>");

        var you = $("<td class='right aligned you'></td>");
        if (round[0] === "C") {
            you.text("Cooperate");
        } else {
            you.text("Defect");
        }
        row.append(you);

        var them = $("<td class='them'></td>");
        if (round[1] === "C") {
            them.text("Cooperate");
        } else {
            them.text("Defect");
        }
        row.append(them);

        return row;
    }

    function updateMatchStatus() {
        var yourYears = 0, theirYears = 0;
        $(".playing .round").each(function(index, round) {
            round = $(round);
            var youPlayed = round.find(".you").text(),
                theyPlayed = round.find(".them").text();
            if (youPlayed === "Cooperate") {
                if (youPlayed === theyPlayed) {
                    yourYears += 2;
                    theirYears += 2;
                } else {
                    yourYears += 5;
                }
            } else {
                if (youPlayed === theyPlayed) {
                    yourYears += 4;
                    theirYears += 4;
                } else {
                    theirYears += 5;
                }
            }
        });
        $(".playing .you-total").text(yourYears);
        $(".playing .them-total").text(theirYears);
        $(".playing .table").removeClass("inverted red green");
        if (yourYears > theirYears) {
            $(".playing .table").addClass("inverted red");
        }
        if (theirYears > yourYears) {
            $(".playing .table").addClass("inverted green");
        }
    }

    function listRounds() {
        $(".playing").show();

        if (roundsSource) {
            roundsSource.close();
        }
        $(".playing .rounds").empty();

        roundsSource = new EventSource("/stream?channel=match:" + matchId);
        roundsSource.addEventListener('round', function(event) {
            var data = JSON.parse(event.data), round = ['X', 'X'];
            $.each(data, function(id, move) {
                if (id === userId) {
                    round[0] = move;
                } else {
                    round[1] = move;
                }
            });
            $(".playing .rounds").append(makeRoundTableRow(round.join('')));
            updateMatchStatus();
            $(".playing .play-next button").removeClass("loading");
        }, false);

        $(".playing .table-container").addClass("loading");
        return $.ajax({
            url: "/matches/" + matchId + "/",
            data: {"id": userId},
            type: "GET",
            success: function(resp) {
                $(".playing .table-container").removeClass("loading");
                var tbody = $(".playing .rounds");
                for (var i=0; i < resp.rounds.length; i++) {
                    var round = resp.rounds[i];
                    if (round[1] === 'X') {
                        $(".playing .play-next button").addClass("loading");
                    } else if (round[0] !== 'X') {
                        tbody.append(makeRoundTableRow(round));
                    }
                }
                updateMatchStatus();
            }
        });
    }

    function bindPlayNextClick() {
        $(".playing .play-next button").click(function() {
            $(this).addClass("loading");
            $.ajax({
                url: "/hint/",
                data: JSON.stringify({
                    id: userId,
                    match: matchId
                }),
                contentType: "application/json",
                type: "POST",
                success: function(resp) {
                    submitMove(resp.move);
                }
            });
        });
    }

    function submitMove(move) {
        $.ajax({
            url: "/matches/" + matchId + "/",
            data: JSON.stringify({
                id: userId,
                move: move
            }),
            contentType: "application/json",
            type: "POST"
        });
    }

    $(".playing").hide();
    if (!userId) {
        showRegistrationModal();
    } else {
        enterLobby().then(listPlayers).then(listMatches);
        bindPlayerClick();
        bindMatchClick();
        bindPlayNextClick();
    }
});
