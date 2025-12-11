using System;
using System.Collections.Generic;
using UnityEngine;

namespace ModernHomm.Core
{
    /// <summary>
    /// Модели данных для синхронизации с бэкендом
    /// </summary>

    [Serializable]
    public class FieldInfo
    {
        public int width;
        public int height;
    }

    [Serializable]
    public class UnitTypeInfo
    {
        public int id;
        public string name;
        public string icon;
        public int damage;
        public int defense;
        public int health;
        public int speed;
        public int range;
        public string image_path;
        public float price;
        public float dodge_chance;
        public float crit_chance;
        public float luck;
        public bool is_kamikaze;
        public float counterattack_chance;
    }

    [Serializable]
    public class UnitInfo
    {
        public int id;
        public int player_id;
        public int x;
        public int y;
        public int count;
        public int hp;
        public float morale;
        public float fatigue;
        public bool has_moved;
        public int deferred;
        public UnitTypeInfo unit_type;
    }

    [Serializable]
    public class ObstacleInfo
    {
        public int x;
        public int y;
    }

    [Serializable]
    public class LogEntry
    {
        public string event_type;
        public string message;
        public string created_at;
    }

    [Serializable]
    public class GameStateResponse
    {
        public int game_id;
        public string status;
        public int player1_id;
        public int player2_id;
        public string player1_name;
        public string player2_name;
        public int current_player_id;
        public int? winner_id;
        public FieldInfo field;
        public List<UnitInfo> units;
        public List<ObstacleInfo> obstacles;
        public List<LogEntry> logs;
    }

    [Serializable]
    public class PlayerInfo
    {
        public int id;
        public string name;
        public string username;
        public float balance;
        public int wins;
        public int losses;
        public float army_cost;
        public List<PlayerUnitInfo> units;
    }

    [Serializable]
    public class PlayerUnitInfo
    {
        public int unit_type_id;
        public string unit_name;
        public int count;
        public float price;
    }

    [Serializable]
    public class PlayersListResponse
    {
        public List<PlayerInfo> players;
    }

    [Serializable]
    public class UnitActionsResponse
    {
        public List<MoveTarget> can_move;
        public List<AttackTarget> can_attack;
    }

    [Serializable]
    public class MoveTarget
    {
        public int x;
        public int y;
    }

    [Serializable]
    public class AttackTarget
    {
        public int id;
        public int x;
        public int y;
    }

    [Serializable]
    public class CreateGameRequest
    {
        public int player1_id;
        public string player2_name;
        public string field_size;
    }

    [Serializable]
    public class CreateGameResponse
    {
        public bool success;
        public int game_id;
        public string message;
    }

    [Serializable]
    public class MoveRequest
    {
        public int unit_id;
        public string action; // "move", "attack", "skip", "defer"
        public int? target_x;
        public int? target_y;
        public int? target_unit_id;
    }

    [Serializable]
    public class MoveResponse
    {
        public bool success;
        public string message;
        public bool turn_switched;
        public string game_status;
        public int? winner_id;
        public int current_player_id;
    }

    [Serializable]
    public class AcceptGameRequest
    {
        public int player_id;
    }

    [Serializable]
    public class PendingGamesResponse
    {
        public List<PendingGame> games;
    }

    [Serializable]
    public class PendingGame
    {
        public int game_id;
        public int player1_id;
        public string player1_name;
        public string field_size;
        public string created_at;
    }

    /// <summary>
    /// Состояние игры на клиенте
    /// </summary>
    public class ClientGameState
    {
        public int GameId { get; set; }
        public int CurrentPlayerId { get; set; }
        public int Player1Id { get; set; }
        public int Player2Id { get; set; }
        public string Player1Name { get; set; }
        public string Player2Name { get; set; }
        public int FieldWidth { get; set; }
        public int FieldHeight { get; set; }
        public string Status { get; set; }
        public int? WinnerId { get; set; }

        public List<UnitInfo> Units { get; set; } = new List<UnitInfo>();
        public List<ObstacleInfo> Obstacles { get; set; } = new List<ObstacleInfo>();
        public List<LogEntry> Logs { get; set; } = new List<LogEntry>();

        public bool IsMyTurn(int myPlayerId) => CurrentPlayerId == myPlayerId;

        public bool IsGameOver => Status == "completed";

        public void UpdateFromResponse(GameStateResponse response)
        {
            GameId = response.game_id;
            Status = response.status;
            Player1Id = response.player1_id;
            Player2Id = response.player2_id;
            Player1Name = response.player1_name;
            Player2Name = response.player2_name;
            CurrentPlayerId = response.current_player_id;
            WinnerId = response.winner_id;

            if (response.field != null)
            {
                FieldWidth = response.field.width;
                FieldHeight = response.field.height;
            }

            Units = response.units ?? new List<UnitInfo>();
            Obstacles = response.obstacles ?? new List<ObstacleInfo>();
            Logs = response.logs ?? new List<LogEntry>();
        }
    }
}
