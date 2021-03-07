export interface Reaction {
  [key: string]: string;
}

export interface Statement {
  parent: number;
  kids: number[];
  text: string;
  reactions: Reaction;
  reply_type: string;
}

export interface Page {
  parent: Statement;
  kids: Statement[];
}
