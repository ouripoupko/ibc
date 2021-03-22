import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { Contract, Method } from './contract';
import { Page } from './statement';

@Injectable({
  providedIn: 'root'
})
export class ContractService {

  private url: string;
  private identity: string;
  private contract: string;

  httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' })
  };

  constructor(
    private http: HttpClient) { }

  getUrl() {
    return this.url;
  }

  getIdentities(server: string): Observable<string[]> {
    this.url = `${server}ibc/app`
    return this.http.get<string[]>(this.url).pipe(
        tap(_ => console.log('fetched identities')),
        catchError(this.handleError<string[]>('getIdentities', []))
      );
  }

  getContracts(identity: string): Observable<Contract[]> {
    this.identity = identity;
    return this.http.get<Contract[]>(`${this.url}/${this.identity}`).pipe(
        tap(_ => console.log('fetched contracts')),
        catchError(this.handleError<Contract[]>('getContracts', []))
      );
  }

  setContract(contract: string) {
    this.contract = contract;
  }

  getStatements(method: Method): Observable<Page> {
    const url = `${this.url}/${this.identity}/${this.contract}`;
    return this.http.put<Page>(url, method, this.httpOptions).pipe(
      tap((page: Page) => console.log(page)),
      catchError(this.handleError<Page>(`getContract name=${name}`))
    );
  }

  createStatement(method: Method): Observable<any> {
    const url = `${this.url}/${this.identity}/${this.contract}`;
    return this.http.put<any>(url, method, this.httpOptions).pipe(
      tap(_ => console.log('created statement')),
      catchError(this.handleError<any>(`createStatement name=${name}`))
    );
  }

  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {

      // TODO: send the error to remote logging infrastructure
      console.error(error); // log to console instead

      // Let the app keep running by returning an empty result.
      return of(result as T);
    };
  }

}
