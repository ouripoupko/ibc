export interface Contract {
  name: string;
  contract: string;
  code: string;
  members: string[];
  methods: Method[];
  values: any[];
  pid: string;
  address: string;
}

export interface Method {
  name: string;
  arguments: string[];
  values: any[];
}
