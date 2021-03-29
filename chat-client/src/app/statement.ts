export interface Reaction {
  [key: string]: string;
}

export interface Statement {
  parent: number;
  me: number;
  kids: number[];
  owner: string;
  text: string;
  reactions: Reaction;
  reply_type: string;
  version: number;
  kids_version: number;
}

export interface Collection {
  [sid: string]: Statement;
}
